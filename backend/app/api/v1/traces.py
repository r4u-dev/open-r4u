"""API endpoints for traces."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.traces import Trace
from app.schemas.traces import TraceCreate, TraceRead
from app.services.traces_service import TracesService

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRead])
async def list_traces(
    session: AsyncSession = Depends(get_session),
) -> list[TraceRead]:
    """Return all traces with their associated input items."""
    query = (
        select(Trace)
        .options(selectinload(Trace.input_items))
        .order_by(Trace.started_at.desc())
    )
    result = await session.execute(query)
    traces: Sequence[Trace] = result.scalars().unique().all()

    return [TraceRead.model_validate(trace) for trace in traces]


@router.post("", response_model=TraceRead, status_code=status.HTTP_201_CREATED)
async def create_trace(
    payload: TraceCreate,
    session: AsyncSession = Depends(get_session),
) -> TraceRead:
    """Create a trace along with its input items."""
    traces_service = TracesService()
    trace = await traces_service.create_trace(payload, session)
    return TraceRead.model_validate(trace)


@router.post("/{trace_id}/group", response_model=TraceRead)
async def group_trace(
    trace_id: int,
    session: AsyncSession = Depends(get_session),
) -> TraceRead:
    """Find or create an implementation for a trace by analyzing similar traces.

    TODO: This endpoint needs to be updated for implementation-based grouping.
    Currently disabled.
    """
    # Check if trace exists
    query = (
        select(Trace)
        .options(selectinload(Trace.input_items))
        .where(Trace.id == trace_id)
    )
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with id {trace_id} not found",
        )

    # TODO: Update grouping logic for implementations
    # task = await find_or_create_task_for_trace(trace_id, session)
    # if task:
    #     trace.implementation_id = task.id
    #     await session.commit()
    #     result = await session.execute(
    #         select(Trace)
    #         .options(selectinload(Trace.input_items))
    #         .where(Trace.id == trace_id),
    #     )
    #     trace = result.scalar_one()

    return TraceRead.model_validate(trace)
