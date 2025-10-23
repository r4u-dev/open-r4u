"""API endpoints for traces."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.projects import Project
from app.models.traces import Trace, TraceInputItem
from app.schemas.traces import TraceCreate, TraceRead
from app.services.implementation_matcher import find_matching_implementation

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
    # Get or create project
    project_query = select(Project).where(Project.name == payload.project)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        # Auto-create project if it doesn't exist
        project = Project(name=payload.project)
        session.add(project)
        await session.flush()

    trace = Trace(
        project_id=project.id,
        model=payload.model,
        result=payload.result,
        error=payload.error,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        path=payload.path,
        implementation_id=payload.implementation_id,
        tools=(
            [tool.model_dump(mode="json", by_alias=True) for tool in payload.tools]
            if payload.tools
            else None
        ),
        instructions=payload.instructions,
        prompt=payload.prompt,
        temperature=payload.temperature,
        tool_choice=(
            payload.tool_choice
            if isinstance(payload.tool_choice, dict)
            else {"type": payload.tool_choice}
            if payload.tool_choice
            else None
        ),
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        total_tokens=payload.total_tokens,
        cached_tokens=payload.cached_tokens,
        reasoning_tokens=payload.reasoning_tokens,
        finish_reason=payload.finish_reason,
        system_fingerprint=payload.system_fingerprint,
        reasoning=(
            payload.reasoning.model_dump(mode="json", exclude_unset=True)
            if payload.reasoning
            else None
        ),
        response_schema=payload.response_schema,
        trace_metadata=payload.trace_metadata,
    )

    for position, item in enumerate(payload.input):
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

    # Auto-match to existing implementation based on system prompt
    if not trace.implementation_id:
        try:
            # Convert input items to list of dicts for matching
            input_items = [item.model_dump(mode="json") for item in payload.input]

            matching = await find_matching_implementation(
                input_items=input_items,
                model=payload.model,
                project_id=project.id,
                session=session,
            )

            if matching:
                trace.implementation_id = matching["implementation_id"]
                trace.prompt_variables = matching["variables"]
                await session.commit()
        except Exception as e:
            # Log but don't fail trace creation if matching fails
            print(f"Failed to auto-match trace {trace.id}: {e}")

    query = (
        select(Trace)
        .options(selectinload(Trace.input_items))
        .where(Trace.id == trace.id)
    )
    result = await session.execute(query)
    created_trace = result.scalar_one()

    return TraceRead.model_validate(created_trace)


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
