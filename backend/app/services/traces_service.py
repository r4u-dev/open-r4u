"""Service for managing trace operations."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace, TraceInputItem, TraceOutputItem
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.schemas.traces import TraceCreate
from app.services.task_grouping import TemplateFinder
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class TracesService:
    """Service for trace operations."""

    def __init__(self):
        """Initialize traces service."""

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

        # Add output items if present
        if trace_data.output:
            for position, item in enumerate(trace_data.output):
                item_data = item.model_dump(mode="json", exclude={"type"})
                trace.output_items.append(
                    TraceOutputItem(
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

            matching = await self._find_matching_implementation(
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

                # Try to create a new implementation from similar traces
                await self._try_create_implementation_from_similar_traces(
                    trace=trace,
                    trace_data=trace_data,
                    project_id=project_id,
                    session=session,
                )

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
            .options(
                joinedload(Trace.input_items),
                joinedload(Trace.output_items),
            )
            .where(Trace.id == trace_id)
        )
        result = await session.execute(query)
        return result.unique().scalar_one()

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

    async def _find_matching_implementation(
        self,
        input_items: list[dict[str, Any]],
        model: str,
        project_id: int,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """Find a matching implementation based on input items and model.

        Args:
            input_items: List of input item dicts
            model: Model name
            project_id: Project ID for scoping
            session: Database session
        Returns:
            Matching implementation info or None

        """
        # Extract the first message as the prompt
        system_prompt = await self._extract_system_prompt_from_trace(input_items)
        if not system_prompt:
            return None

        # Get all implementations for this project and model
        query = (
            select(Implementation)
            .join(Task, Implementation.task_id == Task.id)
            .where(Task.project_id == project_id)
            .where(Implementation.model == model)
        )
        result = await session.execute(query)
        implementations = result.scalars().all()

        if not implementations:
            return None

        # Try to match the system prompt against each implementation's prompt template
        settings = get_settings()
        template_finder = TemplateFinder(
            settings.min_segment_words,
            settings.min_matching_traces,
        )

        for impl in implementations:
            match, variables = template_finder.match_template(
                impl.prompt,
                system_prompt,
            )
            if match:
                return {
                    "implementation_id": impl.id,
                    "variables": variables,
                }

        return None

    async def _try_create_implementation_from_similar_traces(
        self,
        trace: Trace,
        trace_data: TraceCreate,
        project_id: int,
        session: AsyncSession,
    ) -> None:
        """Try to create a new task/implementation by grouping similar traces.

        This is called when no existing implementation matches. It:
        1. Finds all unmatched traces with the same model
        2. If enough similar traces exist, groups them by prompt patterns
        3. For each group, creates a task and implementation with inferred template

        Args:
            trace: The unmatched trace
            trace_data: Original trace creation data
            project_id: Project ID
            session: Database session

        """
        try:
            # Extract first message (instructions)
            input_items = [item.model_dump(mode="json") for item in trace_data.input]
            system_prompt = await self._extract_system_prompt_from_trace(input_items)

            if not system_prompt:
                logger.debug(
                    f"Trace {trace.id} has no first message, skipping auto-grouping",
                )
                return

            settings = get_settings()

            traces_query = (
                select(Trace)
                .where(Trace.project_id == project_id)
                .where(Trace.path == trace.path)
                .where(Trace.implementation_id.is_(None))
                .options(joinedload(Trace.input_items))
            )
            result = await session.execute(traces_query)
            unmatched_traces = result.unique().scalars().all()

            if len(unmatched_traces) < settings.min_cluster_size:
                logger.debug(
                    f"Only {len(unmatched_traces)} unmatched traces with path '{trace.path}', "
                    f"need {settings.min_cluster_size} to auto-create implementation",
                )
                return

            # Extract prompts from all unmatched traces
            prompts = []
            trace_map = {}  # Map index to trace
            for t in unmatched_traces:
                t_input_items = [
                    {"type": item.type.value, **item.data} for item in t.input_items
                ]
                t_prompt = await self._extract_system_prompt_from_trace(t_input_items)
                if t_prompt:
                    prompts.append(t_prompt)
                    trace_map[len(prompts) - 1] = t

            if len(prompts) < settings.min_matching_traces:
                logger.debug(
                    f"Only {len(prompts)} traces with valid prompts, "
                    f"need {settings.min_matching_traces} to auto-create implementation",
                )
                return

            logger.info(
                f"Found {len(prompts)} unmatched traces with prompts, "
                f"attempting to create task/implementation groups",
            )

            # Use TemplateFinder to group similar prompts
            template_finder = TemplateFinder(
                settings.min_segment_words,
                settings.min_matching_traces,
            )

            # Group prompts into templates
            groups = template_finder.group_strings(prompts)

            if not groups:
                logger.debug(
                    f"Could not create any groups for trace {trace.id}",
                )
                return

            # Create task and implementation for each group
            task_service = TaskService(session)

            for template, prompt_indices in groups.items():
                # Create implementation data
                impl_data = ImplementationCreate(
                    prompt=template,
                    model=trace.model,
                    max_output_tokens=trace_data.max_tokens or 1000,
                    temperature=trace_data.temperature,
                    tools=trace_data.tools,
                    tool_choice=trace_data.tool_choice,
                    reasoning=trace_data.reasoning,
                    temp=True,  # Mark as temporary/auto-generated
                )

                # Create task data - name and description will be auto-generated
                task_data = TaskCreate(
                    project=trace.project.name if trace.project else "Default Project",
                    name="",  # Will be auto-generated
                    description="",  # Will be auto-generated
                    implementation=impl_data,
                )

                # Create task with auto-generated name and description
                task = await task_service.create_task(task_data)

                # Get the implementation ID from production_version_id
                if not task.production_version_id:
                    logger.warning(
                        f"Failed to create implementation for task {task.id}, skipping",
                    )
                    continue

                impl_id = task.production_version_id

                # Assign traces to this implementation and extract variables
                for idx in prompt_indices:
                    if idx in trace_map:
                        t = trace_map[idx]
                        match, variables = template_finder.match_template(
                            template,
                            prompts[idx],
                        )
                        if match:
                            t.implementation_id = impl_id
                            t.prompt_variables = variables

                logger.info(
                    f"Created task {task.id} with implementation {impl_id} "
                    f"for {len(prompt_indices)} traces with template: {template}",
                )

            # Commit all changes
            await session.commit()
            await session.refresh(trace)

        except Exception as e:
            logger.warning(
                f"Failed to auto-create implementation from similar traces "
                f"for trace {trace.id}: {e}",
                exc_info=True,
            )

    async def _extract_system_prompt_from_trace(
        self,
        input_items: list[dict[str, Any]],
    ) -> str | None:
        """Extract the system prompt from the trace's input items.

        Args:
            input_items: List of input item dicts

        Returns:
            System prompt string or None

        """
        if not input_items:
            return None

        first_item = input_items[0]
        if first_item.get("type") == "message":
            return first_item.get("content", "")

        return None
