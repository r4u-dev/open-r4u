"""API endpoints for Task execution management."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.models.executions import ExecutionResult
from app.models.tasks import Task
from app.schemas.executions import (
    ExecutionRequest,
    ExecutionResultListItem,
    ExecutionResultRead,
)
from app.services import executions_service as svc

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post(
    "/tasks/{task_id}/execute",
    response_model=ExecutionResultRead,
    status_code=status.HTTP_201_CREATED,
)
async def execute_task(
    task_id: int,
    payload: ExecutionRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExecutionResultRead:
    """Execute a task with optional parameter overrides."""
    
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
    if payload.response_schema is not None:
        overrides["response_schema"] = payload.response_schema
    if payload.reasoning is not None:
        overrides["reasoning"] = payload.reasoning
    
    try:
        execution = await svc.execute(
            session=session,
            settings=settings,
            task_id=task_id,
            variables=payload.variables,
            input=payload.input,
            overrides=overrides if overrides else None,
        )
    except svc.BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}",
        )
    
    return ExecutionResultRead.model_validate(execution)


@router.post(
    "/implementations/{implementation_id}/execute",
    response_model=ExecutionResultRead,
    status_code=status.HTTP_201_CREATED,
)
async def execute_implementation(
    implementation_id: int,
    payload: ExecutionRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExecutionResultRead:
    """Execute a specific implementation with optional variable substitution."""

    try:
        execution = await svc.execute(
            session=session,
            settings=settings,
            implementation_id=implementation_id,
            variables=payload.variables,
            input=payload.input,
        )
    except svc.BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}",
        )

    return ExecutionResultRead.model_validate(execution)


@router.get("/implementations/{implementation_id}/executions", response_model=list[ExecutionResultListItem])
async def list_implementation_executions(
    implementation_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionResultListItem]:
    """List all executions for a specific implementation."""

    try:
        executions = await svc.list_implementation_executions(
            session=session, implementation_id=implementation_id
        )
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    return [ExecutionResultListItem.model_validate(exec) for exec in executions]


@router.get("/tasks/{task_id}/executions", response_model=list[ExecutionResultListItem])
async def list_task_executions(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionResultListItem]:
    """List all executions for a specific task."""

    try:
        executions = await svc.list_task_executions(session=session, task_id=task_id)
    except svc.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    return [ExecutionResultListItem.model_validate(exec) for exec in executions]


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
    task_id: int | None = None,
    implementation_id: int | None = None,
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

