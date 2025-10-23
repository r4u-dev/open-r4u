"""Service for managing trace operations."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.projects import Project
from app.models.traces import Trace, TraceInputItem
from app.schemas.traces import TraceCreate
from app.services.implementation_matcher import find_matching_implementation

logger = logging.getLogger(__name__)


class TracesService:
    """Service for trace operations."""

    async def create_trace(
        self,
        trace_data: TraceCreate,
        session: AsyncSession,
        http_trace_id: int | None = None,
    ) -> Trace:
        """Create a trace with automatic implementation matching.

        Args:
            trace_data: Trace creation data
            session: Database session
            http_trace_id: Optional HTTP trace ID to link

        Returns:
            Created trace with relationships loaded

        """
        # Get or create project
        project = await self._get_or_create_project(
            trace_data.project,
            session,
        )

        # Create trace model
        trace = Trace(
            project_id=project.id,
            http_trace_id=http_trace_id,
            model=trace_data.model,
            result=trace_data.result,
            error=trace_data.error,
            started_at=trace_data.started_at,
            completed_at=trace_data.completed_at,
            path=trace_data.path,
            implementation_id=trace_data.implementation_id,
            tools=self._serialize_tools(trace_data.tools),
            instructions=trace_data.instructions,
            prompt=trace_data.prompt,
            temperature=trace_data.temperature,
            tool_choice=self._serialize_tool_choice(trace_data.tool_choice),
            prompt_tokens=trace_data.prompt_tokens,
            completion_tokens=trace_data.completion_tokens,
            total_tokens=trace_data.total_tokens,
            cached_tokens=trace_data.cached_tokens,
            reasoning_tokens=trace_data.reasoning_tokens,
            finish_reason=trace_data.finish_reason,
            system_fingerprint=trace_data.system_fingerprint,
            reasoning=self._serialize_reasoning(trace_data.reasoning),
            response_schema=trace_data.response_schema,
            trace_metadata=trace_data.trace_metadata,
        )

        # Add input items
        for position, item in enumerate(trace_data.input):
            item_data = item.model_dump(mode="json", exclude={"type"})
            trace.input_items.append(
                TraceInputItem(
                    type=item.type,
                    data=item_data,
                    position=position,
                ),
            )

        # Save trace
        session.add(trace)
        await session.flush()
        await session.commit()

        # Auto-match to implementation if not explicitly set
        if not trace.implementation_id:
            await self._auto_match_implementation(
                trace=trace,
                trace_data=trace_data,
                project_id=project.id,
                session=session,
            )

        # Reload trace with relationships
        return await self._load_trace_with_relationships(trace.id, session)

    async def _get_or_create_project(
        self,
        project_name: str,
        session: AsyncSession,
    ) -> Project:
        """Get existing project or create new one.

        Args:
            project_name: Name of the project
            session: Database session

        Returns:
            Project instance

        """
        query = select(Project).where(Project.name == project_name)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            project = Project(name=project_name)
            session.add(project)
            await session.flush()

        return project

    async def _auto_match_implementation(
        self,
        trace: Trace,
        trace_data: TraceCreate,
        project_id: int,
        session: AsyncSession,
    ) -> None:
        """Attempt to auto-match trace to an implementation.

        Args:
            trace: The trace to match
            trace_data: Original trace creation data
            project_id: Project ID for scoping
            session: Database session

        """
        try:
            # Convert input items to list of dicts for matching
            input_items = [item.model_dump(mode="json") for item in trace_data.input]

            matching = await find_matching_implementation(
                input_items=input_items,
                model=trace_data.model,
                project_id=project_id,
                session=session,
            )

            if matching:
                trace.implementation_id = matching["implementation_id"]
                trace.prompt_variables = matching["variables"]
                await session.commit()
                logger.info(
                    f"Auto-matched trace {trace.id} to implementation "
                    f"{matching['implementation_id']} with variables: "
                    f"{matching['variables']}",
                )
            else:
                logger.debug(f"No implementation match found for trace {trace.id}")

        except Exception as e:
            # Log but don't fail trace creation if matching fails
            logger.warning(
                f"Failed to auto-match trace {trace.id}: {e}",
                exc_info=True,
            )

    async def _load_trace_with_relationships(
        self,
        trace_id: int,
        session: AsyncSession,
    ) -> Trace:
        """Load trace with eager-loaded relationships.

        Args:
            trace_id: ID of the trace to load
            session: Database session

        Returns:
            Trace with relationships loaded

        """
        query = (
            select(Trace)
            .options(selectinload(Trace.input_items))
            .where(Trace.id == trace_id)
        )
        result = await session.execute(query)
        return result.scalar_one()

    def _serialize_tools(
        self,
        tools: list[Any] | None,
    ) -> list[dict[str, Any]] | None:
        """Serialize tool definitions for storage.

        Args:
            tools: List of tool definition objects

        Returns:
            Serialized tools or None

        """
        if not tools:
            return None

        return [tool.model_dump(mode="json", by_alias=True) for tool in tools]

    def _serialize_tool_choice(
        self,
        tool_choice: str | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Serialize tool_choice for storage.

        Args:
            tool_choice: Tool choice configuration

        Returns:
            Serialized tool choice or None

        """
        if not tool_choice:
            return None

        if isinstance(tool_choice, dict):
            return tool_choice

        return {"type": tool_choice}

    def _serialize_reasoning(
        self,
        reasoning: Any | None,
    ) -> dict[str, Any] | None:
        """Serialize reasoning configuration for storage.

        Args:
            reasoning: Reasoning configuration object

        Returns:
            Serialized reasoning or None

        """
        if not reasoning:
            return None

        return reasoning.model_dump(mode="json", exclude_unset=True)
