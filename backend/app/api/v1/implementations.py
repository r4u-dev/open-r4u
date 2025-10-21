"""API endpoints for Implementation management."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.tasks import Implementation
from app.schemas.tasks import ImplementationCreate, ImplementationRead

router = APIRouter(prefix="/implementations", tags=["implementations"])


@router.get("", response_model=list[ImplementationRead])
async def list_implementations(
    model: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ImplementationRead]:
    """Return all implementations, optionally filtered by model."""

    query = select(Implementation)
    if model is not None:
        query = query.where(Implementation.model == model)
    query = query.order_by(Implementation.created_at.desc())

    result = await session.execute(query)
    implementations: Sequence[Implementation] = result.scalars().all()

    return [ImplementationRead.model_validate(impl) for impl in implementations]


@router.get("/{implementation_id}", response_model=ImplementationRead)
async def get_implementation(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
) -> ImplementationRead:
    """Get a specific implementation by ID."""

    query = select(Implementation).where(Implementation.id == implementation_id)
    result = await session.execute(query)
    implementation = result.scalar_one_or_none()

    if not implementation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Implementation with id {implementation_id} not found",
        )

    return ImplementationRead.model_validate(implementation)


@router.post("", response_model=ImplementationRead, status_code=status.HTTP_201_CREATED)
async def create_implementation(
    payload: ImplementationCreate,
    session: AsyncSession = Depends(get_session),
) -> ImplementationRead:
    """Create a new implementation."""

    implementation = Implementation(
        version=payload.version,
        prompt=payload.prompt,
        model=payload.model,
        temperature=payload.temperature,
        reasoning=(
            payload.reasoning.model_dump(mode="json", exclude_unset=True)
            if payload.reasoning
            else None
        ),
        tools=(
            [tool.model_dump(mode="json", by_alias=True) for tool in payload.tools]
            if payload.tools
            else None
        ),
        tool_choice=(
            payload.tool_choice
            if isinstance(payload.tool_choice, dict)
            else {"type": payload.tool_choice}
            if payload.tool_choice
            else None
        ),
        response_schema=payload.response_schema,
        max_output_tokens=payload.max_output_tokens,
    )

    session.add(implementation)
    await session.flush()
    await session.commit()

    query = select(Implementation).where(Implementation.id == implementation.id)
    result = await session.execute(query)
    created_implementation = result.scalar_one()

    return ImplementationRead.model_validate(created_implementation)


@router.put("/{implementation_id}", response_model=ImplementationRead)
async def update_implementation(
    implementation_id: int,
    payload: ImplementationCreate,
    session: AsyncSession = Depends(get_session),
) -> ImplementationRead:
    """Update an existing implementation."""

    query = select(Implementation).where(Implementation.id == implementation_id)
    result = await session.execute(query)
    implementation = result.scalar_one_or_none()

    if not implementation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Implementation with id {implementation_id} not found",
        )

    # Update fields
    implementation.version = payload.version
    implementation.prompt = payload.prompt
    implementation.model = payload.model
    implementation.temperature = payload.temperature
    implementation.reasoning = (
        payload.reasoning.model_dump(mode="json", exclude_unset=True)
        if payload.reasoning
        else None
    )
    implementation.tools = (
        [tool.model_dump(mode="json", by_alias=True) for tool in payload.tools]
        if payload.tools
        else None
    )
    implementation.tool_choice = (
        payload.tool_choice
        if isinstance(payload.tool_choice, dict)
        else {"type": payload.tool_choice}
        if payload.tool_choice
        else None
    )
    implementation.response_schema = payload.response_schema
    implementation.max_output_tokens = payload.max_output_tokens

    await session.commit()
    await session.refresh(implementation)

    return ImplementationRead.model_validate(implementation)


@router.delete("/{implementation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_implementation(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an implementation."""

    query = select(Implementation).where(Implementation.id == implementation_id)
    result = await session.execute(query)
    implementation = result.scalar_one_or_none()

    if not implementation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Implementation with id {implementation_id} not found",
        )

    await session.delete(implementation)
    await session.commit()
