from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.optimizations import OptimizationRunRequest, OptimizationResult
from app.services.optimization_service import OptimizationService
from app.config import get_settings


router = APIRouter(prefix="/optimizations", tags=["optimizations"])


def get_optimization_service() -> OptimizationService:
    return OptimizationService(get_settings())


@router.post("/run", response_model=OptimizationResult, status_code=status.HTTP_200_OK)
async def run_optimization(
    payload: OptimizationRunRequest,
    session: AsyncSession = Depends(get_session),
    optimization_service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationResult:
    try:
        result = await optimization_service.run(
            session=session,
            task_id=payload.task_id,
            max_iterations=payload.max_iterations,
            variants_per_iter=payload.variants_per_iter,
            changeable_fields=payload.changeable_fields,
            improvement_threshold=payload.improvement_threshold,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run optimization: {str(e)}",
        )
