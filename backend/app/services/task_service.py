"""Service for managing task operations."""

from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.services.evaluation_service import EvaluationService
from app.services.implementation_service import ImplementationService
from app.services.openai_client import get_async_openai_client
from app.utils.cost import calculate_traces_cost
from app.utils.statistics import (
    calculate_time_decay_weight,
    calculate_weighted_percentile,
)

PROMPT = """\
An agentic workflow has been given the following instructions:
{instructions}

Create a concise name and description for a task that fulfills these instructions.
"""


class TaskDetails(BaseModel):
    name: str
    description: str


class TaskService:
    """Service for managing task operations."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None):
        """Initialize the service with a database session.

        Args:
            session: Database session for operations
            settings: Optional settings instance (defaults to get_settings())

        """
        self.session = session
        self.settings = settings or get_settings()
        self.implementation_service = ImplementationService(session)
        self.evaluation_service = EvaluationService(self.settings)

    async def get_task(self, task_id: int) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: ID of the task

        Returns:
            Task or None if not found

        """
        query = select(Task).where(Task.id == task_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_tasks(self, project_id: int | None = None) -> list[Task]:
        """List tasks, optionally filtered by project_id.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            List of tasks

        """
        query = select(Task)
        if project_id is not None:
            query = query.where(Task.project_id == project_id)
        query = query.order_by(Task.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_traces_for_task(
        self,
        task_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Trace]:
        """Get all traces for a task (across all implementations).

        Args:
            task_id: ID of the task
            limit: Maximum number of traces to return
            offset: Number of traces to skip for pagination

        Returns:
            List of traces

        """
        # Get all implementation IDs for this task
        impl_query = select(Implementation.id).where(Implementation.task_id == task_id)
        impl_result = await self.session.execute(impl_query)
        implementation_ids = [row[0] for row in impl_result.all()]

        if not implementation_ids:
            return []

        # Query traces for these implementations
        query = select(Trace).where(Trace.implementation_id.in_(implementation_ids))
        query = query.order_by(Trace.started_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def calculate_task_cost_percentile(
        self,
        task_id: int,
        percentile: float = 95.0,
        half_life_hours: float = 168.0,
    ) -> float | None:
        """Calculate the weighted cost percentile for all traces in a task.

        Uses exponential time decay - older traces have less weight.

        Args:
            task_id: ID of the task
            percentile: Percentile to calculate (0-100), defaults to 95
            half_life_hours: Hours for trace weight to decay to 50% (default: 168 = 7 days)

        Returns:
            Cost at the given percentile in USD, or None if no traces

        """
        traces = await self.get_traces_for_task(task_id)
        if not traces:
            return None

        costs = calculate_traces_cost(traces)

        # Calculate time-based weights for each trace
        reference_time = datetime.now(UTC)
        weights = [
            calculate_time_decay_weight(
                trace.started_at,
                reference_time,
                half_life_hours,
            )
            for trace in traces
        ]

        return calculate_weighted_percentile(costs, weights, percentile)

    async def calculate_task_latency_percentile(
        self,
        task_id: int,
        percentile: float = 95.0,
        half_life_hours: float = 168.0,
    ) -> float | None:
        """Calculate the weighted latency percentile for all traces in a task.

        Uses exponential time decay - older traces have less weight.

        Args:
            task_id: ID of the task
            percentile: Percentile to calculate (0-100), defaults to 95
            half_life_hours: Hours for trace weight to decay to 50% (default: 168 = 7 days)

        Returns:
            Latency at the given percentile in seconds, or None if no traces

        """
        traces = await self.get_traces_for_task(task_id)
        if not traces:
            return None

        # Calculate latencies in seconds and corresponding traces
        latencies = []
        trace_times = []
        for trace in traces:
            if trace.completed_at and trace.started_at:
                latency = (trace.completed_at - trace.started_at).total_seconds()
                latencies.append(latency)
                trace_times.append(trace.started_at)

        if not latencies:
            return None

        # Calculate time-based weights for each trace
        reference_time = datetime.now(UTC)
        weights = [
            calculate_time_decay_weight(
                trace_time,
                reference_time,
                half_life_hours,
            )
            for trace_time in trace_times
        ]

        return calculate_weighted_percentile(latencies, weights, percentile)

    async def get_last_activity(self, task_id: int) -> datetime | None:
        """Get the timestamp of the most recent trace for a task.

        Args:
            task_id: ID of the task

        Returns:
            Timestamp of most recent trace, or None if no traces

        """
        traces = await self.get_traces_for_task(task_id, limit=1, offset=0)
        if not traces:
            return None
        return traces[0].started_at

    async def get_task_with_percentiles(
        self,
        task_id: int,
        percentile: float = 95.0,
        half_life_hours: float = 168.0,
    ) -> tuple[Task | None, float | None, float | None, datetime | None]:
        """Get a task with its weighted cost and latency percentiles and last activity.

        Uses exponential time decay - older traces have less weight.

        Args:
            task_id: ID of the task
            percentile: Percentile to calculate (0-100), defaults to 95
            half_life_hours: Hours for trace weight to decay to 50% (default: 168 = 7 days)

        Returns:
            Tuple of (task, cost_percentile, latency_percentile, last_activity)

        """
        task = await self.get_task(task_id)
        if not task:
            return None, None, None, None

        cost_p = await self.calculate_task_cost_percentile(
            task_id,
            percentile,
            half_life_hours,
        )
        latency_p = await self.calculate_task_latency_percentile(
            task_id,
            percentile,
            half_life_hours,
        )
        last_activity = await self.get_last_activity(task_id)

        return task, cost_p, latency_p, last_activity

    async def list_tasks_with_percentiles(
        self,
        project_id: int | None = None,
        percentile: float = 95.0,
        half_life_hours: float = 168.0,
    ) -> list[tuple[Task, float | None, float | None, datetime | None]]:
        """List tasks with their weighted cost and latency percentiles and last activity.

        Uses exponential time decay - older traces have less weight.

        Args:
            project_id: Optional project ID to filter by
            percentile: Percentile to calculate (0-100), defaults to 95
            half_life_hours: Hours for trace weight to decay to 50% (default: 168 = 7 days)

        Returns:
            List of tuples (task, cost_percentile, latency_percentile, last_activity)

        """
        tasks = await self.list_tasks(project_id)

        results = []
        for task in tasks:
            cost_p = await self.calculate_task_cost_percentile(
                task.id,
                percentile,
                half_life_hours,
            )
            latency_p = await self.calculate_task_latency_percentile(
                task.id,
                percentile,
                half_life_hours,
            )
            last_activity = await self.get_last_activity(task.id)
            results.append((task, cost_p, latency_p, last_activity))

        return results

    async def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task with its initial implementation.

        Args:
            task_data: Task creation data including implementation

        Returns:
            Created task

        Raises:
            ValueError: If project doesn't exist

        """
        if not task_data.name or not task_data.description:
            client = get_async_openai_client()
            response = await client.responses.parse(
                model="gpt-4.1",
                input=PROMPT.format(
                    instructions=task_data.implementation.prompt,
                ),
                text_format=TaskDetails,
            )
            if not response.output_parsed:
                raise ValueError("Failed to generate task details from instructions")

            task_data.name = response.output_parsed.name
            task_data.description = response.output_parsed.description

        project = await self._get_or_create_project(task_data.project)

        task = Task(
            project_id=project.id,
            path=task_data.path,
            name=task_data.name,
            description=task_data.description,
            response_schema=task_data.response_schema,
        )
        self.session.add(task)
        await self.session.flush()

        implementation = await self.implementation_service.create_implementation(
            task_id=task.id,
            payload=task_data.implementation,
        )

        task.production_version_id = implementation.id
        await self.session.commit()
        await self.session.refresh(task)

        # Create evaluation config for the task
        await self.evaluation_service.create_or_update_evaluation_config(
            session=self.session,
            task_id=task.id,
        )

        return task

    async def delete_task(self, task_id: int) -> None:
        """Delete a task.

        Args:
            task_id: ID of the task to delete

        Raises:
            ValueError: If task doesn't exist

        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        await self.session.delete(task)
        await self.session.commit()

    async def _get_or_create_project(self, project_name: str) -> Project:
        """Get a project by name or create it if it doesn't exist.

        Args:
            project_name: Name of the project

        Returns:
            Project instance

        """
        query = select(Project).where(Project.name == project_name)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            project = Project(name=project_name)
            self.session.add(project)
            await self.session.flush()

        return project
