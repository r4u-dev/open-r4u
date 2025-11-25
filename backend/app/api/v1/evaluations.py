"""API endpoints for Evaluation and Evaluation Configuration management."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.evaluation import (
    EvaluationConfigCreate,
    EvaluationConfigRead,
    EvaluationConfigUpdate,
    EvaluationListItem,
    EvaluationRead,
    EvaluationResultItem,
    EvaluationRunRequest,
    ImplementationEvaluationStats,
)
from app.services.evaluation_service import (
    BadRequestError,
    EvaluationService,
    NotFoundError,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def get_evaluation_service(
    settings: Settings = Depends(get_settings),
) -> EvaluationService:
    """Dependency to get an EvaluationService instance."""
    return EvaluationService(settings)


# Evaluation Configuration Endpoints
@router.post(
    "/tasks/{task_id}/config",
    response_model=EvaluationConfigRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_evaluation_config(
    task_id: int,
    payload: EvaluationConfigCreate,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationConfigRead:
    """Create or update evaluation configuration for a task."""
    try:
        config = await evaluation_service.create_or_update_evaluation_config(
            session=session,
            task_id=task_id,
            quality_weight=payload.quality_weight,
            cost_weight=payload.cost_weight,
            time_weight=payload.time_weight,
            grader_ids=payload.grader_ids,
        )
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create/update evaluation config: {e!s}",
        )

    return EvaluationConfigRead.model_validate(config)


@router.get("/tasks/{task_id}/config", response_model=EvaluationConfigRead | None)
async def get_evaluation_config(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationConfigRead | None:
    """Get evaluation configuration for a task."""
    try:
        config = await evaluation_service.get_evaluation_config(
            session=session,
            task_id=task_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation config: {e!s}",
        )

    return EvaluationConfigRead.model_validate(config) if config else None


@router.patch("/tasks/{task_id}/config", response_model=EvaluationConfigRead)
async def update_evaluation_config(
    task_id: int,
    payload: EvaluationConfigUpdate,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationConfigRead:
    """Update evaluation configuration for a task."""
    try:
        # Get existing config first
        existing_config = await evaluation_service.get_evaluation_config(
            session=session,
            task_id=task_id,
        )
        if not existing_config:
            raise NotFoundError(f"Evaluation config not found for task {task_id}")

        # Convert payload to dict, excluding None values
        updates = payload.model_dump(exclude_unset=True)

        # Create new config with updated values
        config = await evaluation_service.create_or_update_evaluation_config(
            session=session,
            task_id=task_id,
            quality_weight=updates.get(
                "quality_weight",
                existing_config.quality_weight,
            ),
            cost_weight=updates.get("cost_weight", existing_config.cost_weight),
            time_weight=updates.get("time_weight", existing_config.time_weight),
            trace_evaluation_percentage=updates.get(
                "trace_evaluation_percentage",
                existing_config.trace_evaluation_percentage,
            ),
            grader_ids=updates.get("grader_ids", existing_config.grader_ids),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update evaluation config: {e!s}",
        )

    return EvaluationConfigRead.model_validate(config)


# Evaluation Execution Endpoints
@router.post("", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    payload: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRead:
    """Create and start an evaluation for an implementation. Returns immediately."""
    try:
        # Create the evaluation record
        evaluation = await evaluation_service.create_evaluation(
            session=session,
            implementation_id=payload.implementation_id,
        )

        # Add background task to execute the evaluation
        background_tasks.add_task(
            evaluation_service.execute_evaluation_in_background,
            evaluation_id=evaluation.id,
        )

        # Return the initial evaluation
        return EvaluationRead(
            id=evaluation.id,
            implementation_id=evaluation.implementation_id,
            task_id=evaluation.task_id,
            status=evaluation.status,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
            test_case_count=evaluation.test_case_count,
            error=evaluation.error,
            grader_scores=evaluation.grader_scores,
            quality_score=evaluation.quality_score,
            avg_cost=evaluation.avg_cost,
            avg_execution_time_ms=evaluation.avg_execution_time_ms,
            cost_efficiency_score=None,
            time_efficiency_score=None,
            final_evaluation_score=None,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at,
        )
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create evaluation: {e!s}",
        )


@router.get("", response_model=list[EvaluationListItem])
async def list_evaluations(
    implementation_id: int | None = Query(
        None,
        description="Filter by implementation ID",
    ),
    task_id: int | None = Query(None, description="Filter by task ID"),
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[EvaluationListItem]:
    """List evaluations, optionally filtered by implementation_id or task_id."""
    try:
        evaluations = await evaluation_service.list_evaluations(
            session=session,
            implementation_id=implementation_id,
            task_id=task_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evaluations: {e!s}",
        )

    return evaluations


@router.get("/{evaluation_id}", response_model=EvaluationRead)
async def get_evaluation(
    evaluation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRead:
    """Get evaluation details with calculated metrics."""
    try:
        evaluation = await evaluation_service.get_evaluation(
            session=session,
            evaluation_id=evaluation_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation: {e!s}",
        )

    return evaluation


@router.get("/{evaluation_id}/results", response_model=list[EvaluationResultItem])
async def list_evaluation_results(
    evaluation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[EvaluationResultItem]:
    """List per-execution results (with grades) for an evaluation."""
    try:
        items = await evaluation_service.list_evaluation_results(
            session=session,
            evaluation_id=evaluation_id,
        )
        # Pydantic validation to ensure shape
        return [EvaluationResultItem.model_validate(item) for item in items]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evaluation results: {e!s}",
        )


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> None:
    """Delete an evaluation."""
    try:
        await evaluation_service.delete_evaluation(
            session=session,
            evaluation_id=evaluation_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete evaluation: {e!s}",
        )


@router.post(
    "/tasks/{task_id}/recalculate-target-metrics",
    status_code=status.HTTP_202_ACCEPTED,
)
async def recalculate_target_metrics(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, str]:
    """Recalculate target metrics for a task."""
    try:
        await evaluation_service.calculate_target_metrics(
            session=session,
            task_id=task_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate target metrics: {e!s}",
        )

    return {"message": "Target metrics recalculated successfully"}


@router.get(
    "/implementation/{implementation_id}/stats",
    response_model=ImplementationEvaluationStats,
)
async def get_implementation_evaluation_stats(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> ImplementationEvaluationStats:
    """Get average quality, time, cost, and final evaluation score from all evaluations of an implementation."""
    try:
        return await evaluation_service.get_implementation_evaluation_stats(
            session,
            implementation_id=implementation_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation stats: {e!s}",
        )
