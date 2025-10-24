"""API endpoints for Evaluation and Evaluation Configuration management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.database import get_session
from app.schemas.evaluation import (
    EvaluationConfigCreate,
    EvaluationConfigRead,
    EvaluationConfigUpdate,
    EvaluationRead,
    EvaluationListItem,
)
from app.services.evaluation_service import EvaluationService, NotFoundError, BadRequestError

router = APIRouter(prefix="/evaluations", tags=["evaluations", "evaluation-config"])


def get_evaluation_service(settings: Settings = Depends(get_settings)) -> EvaluationService:
    """Dependency to get an EvaluationService instance."""
    return EvaluationService(settings)


# Evaluation Configuration Endpoints
@router.post(
    "/tasks/{task_id}/evaluation-config",
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
            detail=f"Failed to create/update evaluation config: {str(e)}",
        )

    return EvaluationConfigRead.model_validate(config)


@router.get(
    "/tasks/{task_id}/evaluation-config",
    response_model=EvaluationConfigRead | None,
)
async def get_evaluation_config(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationConfigRead | None:
    """Get evaluation configuration for a task."""
    try:
        config = await evaluation_service.get_evaluation_config(session=session, task_id=task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation config: {str(e)}",
        )

    return EvaluationConfigRead.model_validate(config) if config else None


@router.patch(
    "/tasks/{task_id}/evaluation-config",
    response_model=EvaluationConfigRead,
)
async def update_evaluation_config(
    task_id: int,
    payload: EvaluationConfigUpdate,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationConfigRead:
    """Update evaluation configuration for a task."""
    try:
        # Get existing config first
        existing_config = await evaluation_service.get_evaluation_config(session=session, task_id=task_id)
        if not existing_config:
            raise NotFoundError(f"Evaluation config not found for task {task_id}")
        
        # Convert payload to dict, excluding None values
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        
        # Create new config with updated values
        config = await evaluation_service.create_or_update_evaluation_config(
            session=session,
            task_id=task_id,
            quality_weight=updates.get("quality_weight", existing_config.quality_weight),
            cost_weight=updates.get("cost_weight", existing_config.cost_weight),
            time_weight=updates.get("time_weight", existing_config.time_weight),
            grader_ids=updates.get("grader_ids", existing_config.grader_ids),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update evaluation config: {str(e)}",
        )

    return EvaluationConfigRead.model_validate(config)


# Evaluation Execution Endpoints
@router.post(
    "/implementations/{implementation_id}/evaluations",
    response_model=EvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRead:
    """Run evaluation for an implementation."""
    try:
        evaluation = await evaluation_service.run_evaluation(
            session=session,
            implementation_id=implementation_id,
        )
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run evaluation: {str(e)}",
        )

    # Get the evaluation with calculated scores
    evaluation_with_scores = await evaluation_service.get_evaluation(
        session=session,
        evaluation_id=evaluation.id,
    )

    return evaluation_with_scores


@router.get(
    "/implementations/{implementation_id}/evaluations",
    response_model=list[EvaluationListItem],
)
async def list_implementation_evaluations(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> list[EvaluationListItem]:
    """List all evaluations for an implementation."""
    try:
        evaluations = await evaluation_service.list_evaluations(
            session=session,
            implementation_id=implementation_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evaluations: {str(e)}",
        )

    return evaluations


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationRead,
)
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
            detail=f"Failed to get evaluation: {str(e)}",
        )

    return evaluation


@router.delete(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
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
            detail=f"Failed to delete evaluation: {str(e)}",
        )


@router.post(
    "/tasks/{task_id}/normalization-targets/recalculate",
    status_code=status.HTTP_200_OK,
)
async def recalculate_normalization_targets(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, str]:
    """Recalculate normalization targets for a task."""
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
            detail=f"Failed to recalculate normalization targets: {str(e)}",
        )

    return {"message": "Normalization targets recalculated successfully"}
