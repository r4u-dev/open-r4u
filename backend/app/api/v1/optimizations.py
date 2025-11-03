from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.schemas.optimizations import (
    OptimizationRunRequest,
    OptimizationRead,
    OptimizationListItem,
    OptimizationDashboardResponse,
)
from app.services.optimization_service import OptimizationService
from app.models.optimizations import Optimization
from app.config import get_settings


router = APIRouter(prefix="/optimizations", tags=["optimizations"])


def get_optimization_service() -> OptimizationService:
    return OptimizationService(get_settings())


@router.post("", response_model=OptimizationRead, status_code=status.HTTP_201_CREATED)
async def create_optimization(
    payload: OptimizationRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    optimization_service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRead:
    """Create and start an optimization for a task. Returns immediately."""
    try:
        # Create the optimization record
        optimization = await optimization_service.create_optimization(
            session=session,
            task_id=payload.task_id,
            max_iterations=payload.max_iterations,
            changeable_fields=payload.changeable_fields,
            max_consecutive_no_improvements=payload.patience,
        )
        
        # Add background task to execute the optimization
        background_tasks.add_task(
            optimization_service.execute_optimization_in_background,
            optimization_id=optimization.id,
        )
        
        # Return the initial optimization
        return OptimizationRead.model_validate(optimization)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create optimization: {str(e)}",
        )


@router.get("", response_model=list[OptimizationListItem])
async def list_optimizations(
    task_id: int | None = Query(None, description="Filter by task ID"),
    session: AsyncSession = Depends(get_session),
) -> list[OptimizationListItem]:
    """List optimizations, optionally filtered by task ID."""
    query = select(Optimization)
    if task_id is not None:
        query = query.where(Optimization.task_id == task_id)
    
    query = query.order_by(Optimization.created_at.desc())
    
    result = await session.execute(query)
    optimizations = result.scalars().all()
    
    return [OptimizationListItem.model_validate(opt) for opt in optimizations]


@router.get("/dashboard", response_model=OptimizationDashboardResponse)
async def get_dashboard_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    session: AsyncSession = Depends(get_session),
    optimization_service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationDashboardResponse:
    """Get optimization dashboard metrics and outperforming versions.
    
    Returns summary metrics (score boost, quality boost, money saved) and
    a list of optimized implementations that outperform their production versions.
    
    Args:
        days: Number of days to look back for optimizations (default: 30)
        session: Database session
        optimization_service: Optimization service instance
        
    Returns:
        OptimizationDashboardResponse with summary and outperforming versions
    """
    try:
        return await optimization_service.get_dashboard_metrics(
            session=session,
            days=days,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard metrics: {str(e)}",
        )


@router.get("/{optimization_id}", response_model=OptimizationRead)
async def get_optimization(
    optimization_id: int,
    session: AsyncSession = Depends(get_session),
) -> OptimizationRead:
    """Get optimization details by ID."""
    optimization = await session.scalar(
        select(Optimization).where(Optimization.id == optimization_id)
    )
    
    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization with id {optimization_id} not found",
        )

    return OptimizationRead.model_validate(optimization)
