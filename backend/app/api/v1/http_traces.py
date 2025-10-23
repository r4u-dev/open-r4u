"""API endpoints for HTTP-level trace ingestion."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.http_traces import HTTPTrace
from app.schemas.http_traces import HTTPTraceCreate
from app.schemas.traces import TraceRead
from app.services.http_trace_parser import HTTPTraceParserService
from app.services.traces_service import TracesService

router = APIRouter(prefix="/http-traces", tags=["http-traces"])


@router.post("", response_model=TraceRead, status_code=status.HTTP_201_CREATED)
async def create_http_trace(
    payload: HTTPTraceCreate,
    session: AsyncSession = Depends(get_session),
) -> TraceRead:
    """Create a trace from HTTP-level request/response capture.

    This endpoint accepts raw HTTP request/response data and automatically
    parses it based on the provider (OpenAI, Anthropic, Google, etc.) to
    create a structured trace.

    Args:
        payload: HTTP trace data including raw request/response
        session: Database session

    Returns:
        Created trace with structured data

    Raises:
        HTTPException: If unable to parse the trace or provider is unsupported

    """
    # Convert request/response to strings if they are bytes
    request_str = (
        payload.request.decode("utf-8", errors="replace")
        if isinstance(payload.request, bytes)
        else payload.request
    )
    response_str = (
        payload.response.decode("utf-8", errors="replace")
        if isinstance(payload.response, bytes)
        else payload.response
    )

    # Create and persist HTTPTrace first
    http_trace = HTTPTrace(
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        status_code=payload.status_code,
        error=payload.error,
        request=request_str,
        request_headers=payload.request_headers,
        response=response_str,
        response_headers=payload.response_headers,
        http_metadata=payload.metadata,
    )
    session.add(http_trace)
    await session.flush()

    # Initialize parser service
    parser_service = HTTPTraceParserService()

    # Parse the HTTP trace into a TraceCreate object
    try:
        trace_create = parser_service.parse_http_trace(
            request=payload.request,
            request_headers=payload.request_headers,
            response=payload.response,
            response_headers=payload.response_headers,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
            status_code=payload.status_code,
            error=payload.error,
            metadata=payload.metadata,
        )
    except ValueError as e:
        # HTTPTrace is already saved, just rollback the transaction for the trace
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse HTTP trace: {e!s}",
        )
    except Exception as e:
        # HTTPTrace is already saved, just rollback the transaction for the trace
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error parsing HTTP trace: {e!s}",
        )

    # Create trace using service (handles project creation, matching, etc.)
    traces_service = TracesService()
    trace = await traces_service.create_trace(
        trace_create,
        session,
        http_trace_id=http_trace.id,
    )

    return TraceRead.model_validate(trace)
