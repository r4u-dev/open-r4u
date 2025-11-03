"""API endpoints for Task execution management."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.executions import (
    ExecutionRequest,
    ExecutionResultListItem,
    ExecutionResultRead,
)
from app.services import executions_service as svc

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("", response_model=ExecutionResultRead, status_code=status.HTTP_201_CREATED)
async def execute(
    payload: ExecutionRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExecutionResultRead:
    """Execute a task or implementation with optional parameter overrides.
    
    The request body must specify either task_id OR implementation_id.
    Option overrides (model, temperature, etc.) are only supported when executing by task_id.
    """
    # Extract overrides from payload
    overrides = {}
    if payload.model is not None:
        overrides["model"] = payload.model
    if payload.temperature is not None:
        overrides["temperature"] = payload.temperature
    if payload.max_output_tokens is not None:
        overrides["max_output_tokens"] = payload.max_output_tokens
    if payload.tools is not None:
        overrides["tools"] = payload.tools
    if payload.tool_choice is not None:
        overrides["tool_choice"] = payload.tool_choice
    if payload.reasoning is not None:
        overrides["reasoning"] = payload.reasoning

    try:
        execution = await svc.execute(
            session=session,
            settings=settings,
            task_id=payload.task_id,
            implementation_id=payload.implementation_id,
            arguments=payload.arguments,
            overrides=overrides if overrides else None,
        )
    except svc.BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {e!s}",
        )

    return ExecutionResultRead.model_validate(execution)


@router.get("/{execution_id}", response_model=ExecutionResultRead)
async def get_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session),
) -> ExecutionResultRead:
    """Get a specific execution result by ID."""
    try:
        execution = await svc.get_execution(session=session, execution_id=execution_id)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    return ExecutionResultRead.model_validate(execution)


@router.get("", response_model=list[ExecutionResultListItem])
async def list_executions(
    task_id: int | None = Query(None, description="Filter by task ID"),
    implementation_id: int | None = Query(None, description="Filter by implementation ID"),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionResultListItem]:
    """List all executions, optionally filtered by task_id or implementation_id."""
    executions = await svc.list_executions(
        session=session,
        task_id=task_id,
        implementation_id=implementation_id,
    )
    return [ExecutionResultListItem.model_validate(exec) for exec in executions]


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an execution result."""
    try:
        await svc.delete_execution(session=session, execution_id=execution_id)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete execution: {e!s}",
        )
