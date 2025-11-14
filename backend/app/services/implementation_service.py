"""Service for managing implementation operations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ItemType
from app.models.tasks import Implementation, Task
from app.schemas.tasks import ImplementationCreate, ImplementationUpdate
from app.services.provider_service import ProviderService
from app.services.task_grouping import TemplateFinder
from app.services.traces_service import TracesService


class ImplementationService:
    """Service for managing implementation operations."""

    def __init__(self, session: AsyncSession):
        """Initialize the service with a database session.

        Args:
            session: Database session for operations

        """
        self.session = session
        self.provider_service = ProviderService(session)

    async def get_implementation(self, implementation_id: int) -> Implementation | None:
        """Get an implementation by ID.

        Args:
            implementation_id: ID of the implementation

        Returns:
            Implementation or None if not found

        """
        query = select(Implementation).where(Implementation.id == implementation_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_implementations(
        self,
        task_id: int | None = None,
    ) -> list[Implementation]:
        """List implementations, optionally filtered by task_id.

        Args:
            task_id: Optional task ID to filter by

        Returns:
            List of implementations

        """
        query = select(Implementation)
        if task_id is not None:
            query = query.where(Implementation.task_id == task_id)
        query = query.order_by(Implementation.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_implementation(
        self,
        task_id: int,
        payload: ImplementationCreate,
    ) -> Implementation:
        """Create a new implementation for a task.

        Args:
            task_id: ID of the task to create implementation for
            payload: Implementation creation data

        Returns:
            Created implementation

        Raises:
            ValueError: If task doesn't exist

        """
        # Verify task exists
        task = await self._get_task(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        # Create implementation
        implementation = Implementation(
            task_id=task_id,
            version=payload.version,
            prompt=payload.prompt,
            model=await self.provider_service.canonicalize_model(payload.model),
            temperature=payload.temperature,
            reasoning=self._serialize_reasoning(payload.reasoning),
            tools=self._serialize_tools(payload.tools),
            tool_choice=self._serialize_tool_choice(payload.tool_choice),
            max_output_tokens=payload.max_output_tokens,
        )

        self.session.add(implementation)
        await self.session.flush()
        await self.session.commit()

        # Reload to get all relationships
        await self.session.refresh(implementation)
        return implementation

    async def update_implementation(
        self,
        implementation_id: int,
        payload: ImplementationUpdate,
    ) -> Implementation:
        """Update an existing implementation.

        Args:
            implementation_id: ID of the implementation to update
            payload: Implementation update data

        Returns:
            Updated implementation

        Raises:
            ValueError: If implementation doesn't exist

        """
        implementation = await self.get_implementation(implementation_id)
        if not implementation:
            raise ValueError(f"Implementation with id {implementation_id} not found")

        # Update fields
        if payload.prompt:
            implementation.prompt = payload.prompt

            traces_service = TracesService()
            traces = await traces_service.list_traces(self.session, implementation.id)
            tf = TemplateFinder()
            for trace in traces:
                if not trace.input_items:
                    continue
                if trace.input_items[0].type != ItemType.MESSAGE:
                    continue
                instructions = trace.input_items[0].data.get("content", "")
                match, variables = tf.match_template(
                    implementation.prompt,
                    instructions,
                )
                if not match:
                    trace.implementation_id = None
                else:
                    trace.prompt_variables = variables

        await self.session.commit()
        await self.session.refresh(implementation)
        return implementation

    async def delete_implementation(self, implementation_id: int) -> None:
        """Delete an implementation.

        Args:
            implementation_id: ID of the implementation to delete

        Raises:
            ValueError: If implementation doesn't exist

        """
        implementation = await self.get_implementation(implementation_id)
        if not implementation:
            raise ValueError(f"Implementation with id {implementation_id} not found")

        await self.session.delete(implementation)
        await self.session.commit()

    async def set_production_version(self, implementation_id: int) -> Implementation:
        """Set an implementation as the production version for its task.

        Args:
            implementation_id: ID of the implementation to set as production

        Returns:
            Updated implementation

        Raises:
            ValueError: If implementation doesn't exist

        """
        implementation = await self.get_implementation(implementation_id)
        if not implementation:
            raise ValueError(f"Implementation with id {implementation_id} not found")

        # Get the task
        task = await self._get_task(implementation.task_id)
        if not task:
            raise ValueError(f"Task with id {implementation.task_id} not found")

        # Set as production version
        task.production_version_id = implementation.id
        await self.session.commit()
        await self.session.refresh(implementation)
        return implementation

    async def _get_task(self, task_id: int) -> Task | None:
        """Get a task by ID (internal helper).

        Args:
            task_id: ID of the task

        Returns:
            Task or None if not found

        """
        query = select(Task).where(Task.id == task_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _serialize_reasoning(reasoning: Any) -> dict[str, Any] | None:
        """Serialize reasoning configuration to dict.

        Args:
            reasoning: Reasoning configuration

        Returns:
            Serialized reasoning dict or None

        """
        if reasoning is None:
            return None
        return reasoning.model_dump(mode="json", exclude_unset=True)

    @staticmethod
    def _serialize_tools(tools: list[Any] | None) -> list[dict[str, Any]] | None:
        """Serialize tools list to dict list.

        Args:
            tools: List of tool definitions

        Returns:
            Serialized tools list or None

        """
        if tools is None:
            return None
        return [tool.model_dump(mode="json", by_alias=True) for tool in tools]

    @staticmethod
    def _serialize_tool_choice(
        tool_choice: str | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Serialize tool_choice to dict.

        Args:
            tool_choice: Tool choice configuration (string or dict)

        Returns:
            Serialized tool_choice dict or None

        """
        if tool_choice is None:
            return None
        if isinstance(tool_choice, dict):
            return tool_choice
        return {"type": tool_choice}


# Helper function for backward compatibility
async def create_implementation(
    task_id: int,
    payload: ImplementationCreate,
    session: AsyncSession,
) -> Implementation:
    """Create a new implementation (backward compatibility helper).

    Args:
        task_id: ID of the task
        payload: Implementation creation data
        session: Database session

    Returns:
        Created implementation

    """
    service = ImplementationService(session)
    return await service.create_implementation(task_id, payload)
