"""API endpoints for HTTP-level trace ingestion."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.http_traces import HTTPTrace
from app.models.projects import Project
from app.models.traces import Trace, TraceInputItem
from app.schemas.http_traces import HTTPTraceCreate
from app.schemas.traces import TraceRead
from app.services.http_trace_parser import HTTPTraceParserService

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

    # Get or create project
    project_query = select(Project).where(Project.name == trace_create.project)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        # Auto-create project if it doesn't exist
        project = Project(name=trace_create.project)
        session.add(project)
        await session.flush()

    # Create trace and link to HTTPTrace
    trace = Trace(
        project_id=project.id,
        http_trace_id=http_trace.id,
        model=trace_create.model,
        result=trace_create.result,
        error=trace_create.error,
        started_at=trace_create.started_at,
        completed_at=trace_create.completed_at,
        path=trace_create.path,
        implementation_id=trace_create.implementation_id,
        tools=(
            [tool.model_dump(mode="json", by_alias=True) for tool in trace_create.tools]
            if trace_create.tools
            else None
        ),
        instructions=trace_create.instructions,
        prompt=trace_create.prompt,
        temperature=trace_create.temperature,
        tool_choice=(
            trace_create.tool_choice
            if isinstance(trace_create.tool_choice, dict)
            else {"type": trace_create.tool_choice}
            if trace_create.tool_choice
            else None
        ),
        prompt_tokens=trace_create.prompt_tokens,
        completion_tokens=trace_create.completion_tokens,
        total_tokens=trace_create.total_tokens,
        cached_tokens=trace_create.cached_tokens,
        reasoning_tokens=trace_create.reasoning_tokens,
        finish_reason=trace_create.finish_reason,
        system_fingerprint=trace_create.system_fingerprint,
        reasoning=(
            trace_create.reasoning.model_dump(mode="json", exclude_unset=True)
            if trace_create.reasoning
            else None
        ),
        response_schema=trace_create.response_schema,
        trace_metadata=trace_create.trace_metadata,
    )

    # Add input items
    for position, item in enumerate(trace_create.input):
        # Convert each input item to a dict for storage
        item_data = item.model_dump(mode="json", exclude={"type"})
        trace.input_items.append(
            TraceInputItem(
                type=item.type,
                data=item_data,
                position=position,
            ),
        )

    session.add(trace)
    await session.flush()
    await session.commit()

    # Fetch the created trace with relationships
    query = (
        select(Trace)
        .options(selectinload(Trace.input_items))
        .where(Trace.id == trace.id)
    )
    result = await session.execute(query)
    created_trace = result.scalar_one()

    return TraceRead.model_validate(created_trace)
