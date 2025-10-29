"""API endpoints for traces."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_session
from app.models.http_traces import HTTPTrace
from app.models.traces import Trace
from app.schemas.http_traces import HTTPTraceRead
from app.schemas.traces import TraceCreate, TraceRead
from app.services.traces_service import TracesService

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRead])
async def list_traces(
    limit: int = Query(25, ge=1, le=100, description="Number of traces to return"),
    offset: int = Query(0, ge=0, description="Number of traces to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[TraceRead]:
    """Return paginated traces with their associated input items.

    Supports infinite scrolling with limit and offset parameters.
    """
    query = (
        select(Trace)
        .options(
            joinedload(Trace.input_items),
            joinedload(Trace.output_items),
        )
        .order_by(Trace.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    traces: Sequence[Trace] = result.unique().scalars().all()

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
        .options(
            joinedload(Trace.input_items),
            joinedload(Trace.output_items),
        )
        .where(Trace.id == trace_id)
    )
    result = await session.execute(query)
    trace = result.unique().scalar_one_or_none()

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


@router.get("/{trace_id}/http-trace", response_model=HTTPTraceRead)
async def get_trace_http_trace(
    trace_id: int,
    session: AsyncSession = Depends(get_session),
) -> HTTPTraceRead:
    """Get the HTTP trace data associated with a specific trace.

    This endpoint returns the raw HTTP request/response data that was captured
    for debugging purposes.

    Args:
        trace_id: The ID of the trace
        session: Database session

    Returns:
        HTTPTraceRead: The HTTP trace data

    Raises:
        HTTPException: If trace not found or has no associated HTTP trace

    """
    # First check if the trace exists
    query = select(Trace).where(Trace.id == trace_id)
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with id {trace_id} not found",
        )

    if not trace.http_trace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} has no associated HTTP trace",
        )

    # Fetch the HTTP trace
    query = select(HTTPTrace).where(HTTPTrace.id == trace.http_trace_id)
    result = await session.execute(query)
    http_trace = result.scalar_one_or_none()

    if not http_trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTTP trace not found",
        )

    return HTTPTraceRead.model_validate(http_trace)
