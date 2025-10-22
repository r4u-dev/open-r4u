from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.projects import Project
from app.models.traces import Trace, TraceInputItem
from app.schemas.traces import TraceCreate, TraceRead
from app.services.task_grouping import (
    find_or_create_task_for_trace,
    try_match_existing_task,
)

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRead])
async def list_traces(
    session: AsyncSession = Depends(get_session),
) -> list[TraceRead]:
    """Return all traces with their associated input items."""
    query = select(Trace).options(selectinload(Trace.input_items)).order_by(Trace.started_at.desc())
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
        task_id=payload.task_id,
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
            else {"type": payload.tool_choice} if payload.tool_choice else None
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

    # Auto-match to existing task (fast - only queries existing tasks)
    # Don't create new tasks here to keep creation fast
    if not trace.task_id:
        try:
            matching_task = await try_match_existing_task(trace.id, session)
            if matching_task:
                trace.task_id = matching_task.id
                await session.commit()
        except Exception as e:
            # Log but don't fail trace creation if grouping fails
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
    """Find or create a task for a trace by analyzing similar traces.
    
    This endpoint:
    1. Extracts instructions from the trace
    2. Compares with existing tasks
    3. If no match, finds similar traces and creates a new task
    4. Assigns the trace to the task
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

    # Try to find or create task
    task = await find_or_create_task_for_trace(trace_id, session)

    if task:
        trace.task_id = task.id
        await session.commit()

        # Reload trace with eager-loaded input_items
        result = await session.execute(
            select(Trace)
            .options(selectinload(Trace.input_items))
            .where(Trace.id == trace_id),
        )
        trace = result.scalar_one()

    return TraceRead.model_validate(trace)
