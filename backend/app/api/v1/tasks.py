"""API endpoints for Task management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.tasks import TaskCreate, TaskSchema
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    session: AsyncSession = Depends(get_session),
) -> TaskService:
    """Dependency provider for TaskService."""
    return TaskService(session)


@router.get("", response_model=list[TaskSchema])
async def list_tasks(
    project_id: int | None = None,
    percentile: float = Query(
        95.0,
        ge=0,
        le=100,
        description="Percentile for cost and latency metrics",
    ),
    half_life_hours: float = Query(
        168.0,
        gt=0,
        description="Hours for trace weight to decay to 50% (default: 168 = 7 days)",
    ),
    service: TaskService = Depends(get_task_service),
) -> list[TaskSchema]:
    """Return all tasks with time-weighted cost and latency percentiles, optionally filtered by project_id.

    Uses exponential time decay - older traces have exponentially less weight in the calculation.
    """
    tasks_with_percentiles = await service.list_tasks_with_percentiles(
        project_id=project_id,
        percentile=percentile,
        half_life_hours=half_life_hours,
    )

    result = []
    for task, cost_p, latency_p, last_activity in tasks_with_percentiles:
        task_dict = TaskSchema.model_validate(task).model_dump()
        task_dict["cost_percentile"] = cost_p
        task_dict["latency_percentile"] = latency_p
        task_dict["last_activity"] = last_activity
        result.append(TaskSchema.model_validate(task_dict))

    return result


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(
    task_id: int,
    percentile: float = Query(
        95.0,
        ge=0,
        le=100,
        description="Percentile for cost and latency metrics",
    ),
    half_life_hours: float = Query(
        168.0,
        gt=0,
        description="Hours for trace weight to decay to 50% (default: 168 = 7 days)",
    ),
    service: TaskService = Depends(get_task_service),
) -> TaskSchema:
    """Get a specific task by ID with time-weighted cost and latency percentiles.

    Uses exponential time decay - older traces have exponentially less weight in the calculation.
    """
    task, cost_p, latency_p, last_activity = await service.get_task_with_percentiles(
        task_id=task_id,
        percentile=percentile,
        half_life_hours=half_life_hours,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )

    task_dict = TaskSchema.model_validate(task).model_dump()
    task_dict["cost_percentile"] = cost_p
    task_dict["latency_percentile"] = latency_p
    task_dict["last_activity"] = last_activity
    return TaskSchema.model_validate(task_dict)


@router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskSchema:
    """Create a new task."""
    try:
        task = await service.create_task(payload)
        return TaskSchema.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> None:
    """Delete a task."""
    try:
        await service.delete_task(task_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/group-traces",
    response_model=list[TaskSchema],
    status_code=status.HTTP_201_CREATED,
)
async def group_traces_into_tasks(
    session: AsyncSession = Depends(get_session),
    similarity_threshold: float = 0.6,
    min_cluster_size: int = 2,
) -> list[TaskSchema]:
    """Automatically group all ungrouped traces into tasks.

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

    return [TaskSchema.model_validate(task) for task in created_tasks]
