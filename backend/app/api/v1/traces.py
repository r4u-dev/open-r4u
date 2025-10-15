from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.projects import Project
from app.models.traces import Trace, TraceMessage
from app.schemas.traces import TraceCreate, TraceRead

router = APIRouter(prefix="/traces", tags=["traces"])

@router.get("", response_model=list[TraceRead])
async def list_traces(
    session: AsyncSession = Depends(get_session),
) -> list[TraceRead]:
    """Return all traces with their associated messages."""

    query = select(Trace).options(selectinload(Trace.messages)).order_by(Trace.started_at.desc())
    result = await session.execute(query)
    traces: Sequence[Trace] = result.scalars().unique().all()

    return [TraceRead.model_validate(trace) for trace in traces]



@router.post("", response_model=TraceRead, status_code=status.HTTP_201_CREATED)
async def create_trace(
    payload: TraceCreate,
    session: AsyncSession = Depends(get_session),
) -> TraceRead:
    """Create a trace along with its messages."""

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
        tools=
        [tool.model_dump(mode="json", by_alias=True) for tool in payload.tools]
        if payload.tools
        else None,
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        total_tokens=payload.total_tokens,
        response_schema=payload.response_schema,
        trace_metadata=payload.trace_metadata,
    )

    for position, message in enumerate(payload.messages):
        trace.messages.append(
            TraceMessage(
                role=message.role,
                content=message.content,
                position=position,
                name=message.name,
                tool_call_id=message.tool_call_id,
                tool_calls=
                [tool_call.model_dump(mode="json") for tool_call in message.tool_calls]
                if message.tool_calls
                else None,
            )
        )

    session.add(trace)
    await session.flush()
    await session.commit()

    query = (
        select(Trace)
        .options(selectinload(Trace.messages))
        .where(Trace.id == trace.id)
    )
    result = await session.execute(query)
    created_trace = result.scalar_one()

    return TraceRead.model_validate(created_trace)
