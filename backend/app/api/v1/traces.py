from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.traces import Trace, TraceMessage
from app.schemas.traces import (
    MessageRead,
    TraceCreate,
    TraceRead,
)

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("", response_model=TraceRead, status_code=status.HTTP_201_CREATED)
async def create_trace(
    payload: TraceCreate,
    session: AsyncSession = Depends(get_session),
) -> TraceRead:
    """Create a trace along with its messages."""

    trace = Trace(
        model=payload.model,
        result=payload.result,
        error=payload.error,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
    )

    for position, message in enumerate(payload.messages):
        trace.messages.append(
            TraceMessage(
                role=message.role,
                content=message.content,
                position=position,
            )
        )

    session.add(trace)
    await session.commit()
    await session.refresh(trace)

    return TraceRead(
        id=trace.id,
        messages=[
            MessageRead(id=message.id, role=message.role, content=message.content)
            for message in trace.messages
        ],
        model=trace.model,
        result=trace.result,
        error=trace.error,
        started_at=trace.started_at,
        completed_at=payload.completed_at,
    )
