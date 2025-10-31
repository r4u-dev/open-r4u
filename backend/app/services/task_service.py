"""Service for managing task operations."""

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.tasks import Task
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.services.implementation_service import ImplementationService
from app.services.openai_client import get_async_openai_client

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

    def __init__(self, session: AsyncSession):
        """Initialize the service with a database session.

        Args:
            session: Database session for operations

        """
        self.session = session
        self.implementation_service = ImplementationService(session)

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


async def create_task(task_data: TaskCreate, session: AsyncSession) -> Task:
    """Create a new task (backward compatibility helper).

    Args:
        task_data: Task creation data
        session: Database session

    Returns:
        Created task

    """
    service = TaskService(session)
    return await service.create_task(task_data)


async def create_task_with_implementation(
    project_id: int,
    path: str | None,
    name: str,
    description: str,
    response_schema: dict | None,
    implementation_data: ImplementationCreate,
    session: AsyncSession,
) -> Task:
    """Create a task with its initial implementation (for internal use).

    This function is used by services like task_grouping that need to create
    tasks programmatically without the full TaskCreate schema.

    Args:
        project_id: ID of the project
        path: Optional path for the task
        name: Task name
        description: Task description
        response_schema: Optional response schema
        implementation_data: Implementation creation data
        session: Database session

    Returns:
        Created task with implementation

    """
    # Create task
    task = Task(
        project_id=project_id,
        path=path,
        name=name,
        description=description,
        response_schema=response_schema,
    )
    session.add(task)
    await session.flush()

    # Create implementation
    implementation_service = ImplementationService(session)
    implementation = await implementation_service.create_implementation(
        task_id=task.id,
        payload=implementation_data,
    )

    # Set as production version
    task.production_version_id = implementation.id
    await session.flush()

    return task
