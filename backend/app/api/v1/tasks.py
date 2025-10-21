"""API endpoints for Task management."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.schemas.tasks import TaskCreate, TaskRead
from app.services.task_grouping import group_all_traces

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    project_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[TaskRead]:
    """Return all tasks, optionally filtered by project_id."""

    query = select(Task)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    query = query.order_by(Task.created_at.desc())

    result = await session.execute(query)
    tasks: Sequence[Task] = result.scalars().all()

    return [TaskRead.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    """Get a specific task by ID."""

    query = select(Task).where(Task.id == task_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    return TaskRead.model_validate(task)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    """Create a new task."""

    # Get or create project
    project_query = select(Project).where(Project.name == payload.project)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        # Auto-create project if it doesn't exist
        project = Project(name=payload.project)
        session.add(project)
        await session.flush()

    # Create implementation
    implementation = Implementation(
        version=payload.implementation.version,
        prompt=payload.implementation.prompt,
        model=payload.implementation.model,
        temperature=payload.implementation.temperature,
        reasoning=(
            payload.implementation.reasoning.model_dump(mode="json", exclude_unset=True)
            if payload.implementation.reasoning
            else None
        ),
        tools=(
            [
                tool.model_dump(mode="json", by_alias=True)
                for tool in payload.implementation.tools
            ]
            if payload.implementation.tools
            else None
        ),
        tool_choice=(
            payload.implementation.tool_choice
            if isinstance(payload.implementation.tool_choice, dict)
            else {"type": payload.implementation.tool_choice}
            if payload.implementation.tool_choice
            else None
        ),
        response_schema=payload.implementation.response_schema,
        max_output_tokens=payload.implementation.max_output_tokens,
    )
    session.add(implementation)
    await session.flush()

    # Create task
    task = Task(
        project_id=project.id,
        implementation_id=implementation.id,
        path=payload.path,
    )
    session.add(task)
    await session.flush()
    await session.commit()

    query = select(Task).where(Task.id == task.id)
    result = await session.execute(query)
    created_task = result.scalar_one()

    return TaskRead.model_validate(created_task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a task."""

    query = select(Task).where(Task.id == task_id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    await session.delete(task)
    await session.commit()


@router.post(
    "/group-traces", response_model=list[TaskRead], status_code=status.HTTP_201_CREATED
)
async def group_traces_into_tasks(
    session: AsyncSession = Depends(get_session),
    similarity_threshold: float = 0.6,
    min_cluster_size: int = 2,
) -> list[TaskRead]:
    """
    Automatically group all ungrouped traces into tasks.

    This endpoint:
    1. Finds all traces without a task_id
    2. Groups them by path
    3. Within each path, groups by instruction similarity
    4. Infers templates for each group
    5. Creates tasks with templated instructions
    6. Assigns traces to their tasks

    Args:
        similarity_threshold: Minimum similarity to group traces (0.0-1.0, default 0.6)
        min_cluster_size: Minimum traces needed to create a task (default 2)

    Returns:
        List of created tasks
    """
    created_tasks = await group_all_traces(
        session,
        similarity_threshold=similarity_threshold,
        min_cluster_size=min_cluster_size,
    )

    return [TaskRead.model_validate(task) for task in created_tasks]
