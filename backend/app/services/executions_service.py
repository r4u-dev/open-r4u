"""Service layer for execution operations.

This module encapsulates all database interactions for executions so that
the API layer remains free of direct SQL/ORM queries.
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.models.executions import ExecutionResult
from app.models.tasks import Implementation, Task
from app.services.executor import LLMExecutor
from app.schemas.traces import InputItem


class NotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BadRequestError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


async def _create_temp_implementation(
    session: AsyncSession,
    base_implementation: Implementation,
    overrides: dict[str, Any],
) -> Implementation:
    """Create a temporary implementation with overrides applied."""
    
    # Create new implementation with overrides
    temp_impl = Implementation(
        version=f"{base_implementation.version}-temp",
        prompt=base_implementation.prompt,
        model=overrides.get("model", base_implementation.model),
        temperature=overrides.get("temperature", base_implementation.temperature),
        reasoning=overrides.get("reasoning", base_implementation.reasoning),
        tools=overrides.get("tools", base_implementation.tools),
        tool_choice=overrides.get("tool_choice", base_implementation.tool_choice),
        response_schema=overrides.get("response_schema", base_implementation.response_schema),
        max_output_tokens=overrides.get("max_output_tokens", base_implementation.max_output_tokens),
        temp=True,
    )
    
    session.add(temp_impl)
    await session.commit()
    await session.refresh(temp_impl)
    
    return temp_impl


async def execute(
    session: AsyncSession,
    settings: Settings,
    task_id: int | None = None,
    implementation_id: int | None = None,
    variables: dict[str, Any] | None = None,
    input: list[InputItem] | None = None,
    overrides: dict[str, Any] | None = None,
) -> ExecutionResult:
    """Unified execution entrypoint.

    - If task_id is provided, executes the task's implementation.
      When overrides are provided, a temporary implementation is auto-created.
    - If implementation_id is provided, executes that implementation (overrides are not allowed).
    - input: Optional message history (InputItem list). If provided, overrides prompt rendering.
    """

    if (task_id is None) == (implementation_id is None):
        raise BadRequestError("Provide exactly one of task_id or implementation_id")

    # Resolve implementation and related task
    if task_id is not None:
        # Load task with implementation
        query = (
            select(Task)
            .options(selectinload(Task.production_version))
            .where(Task.id == task_id)
        )
        result = await session.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")

        implementation = task.production_version
        if not implementation:
            raise NotFoundError(f"Production version not found for task {task_id}")

        # If overrides provided, create temporary implementation
        if overrides and any(overrides.values()):
            implementation = await _create_temp_implementation(
                session, implementation, overrides
            )

        resolved_task_id = task.id
        resolved_impl_id = implementation.id

    else:
        # implementation_id path does not support overrides
        if overrides and any(overrides.values()):
            raise BadRequestError(
                "Overrides are only supported when executing by task_id"
            )

        # Load implementation with tasks to determine associated task
        query = (
            select(Implementation)
            .options(selectinload(Implementation.task))
            .where(Implementation.id == implementation_id)
        )
        result = await session.execute(query)
        implementation = result.scalar_one_or_none()
        if not implementation:
            raise NotFoundError(
                f"Implementation with id {implementation_id} not found"
            )
        if not implementation.task:
            raise BadRequestError(
                f"No task found for implementation {implementation_id}"
            )

        task = implementation.task
        resolved_task_id = task.id
        resolved_impl_id = implementation.id

    # Execute via LLM executor
    executor = LLMExecutor(settings)
    service_result = await executor.execute(implementation, variables, input)

    # Persist execution
    db_execution = ExecutionResult(
        task_id=resolved_task_id,
        implementation_id=resolved_impl_id,
        started_at=service_result.started_at,
        completed_at=service_result.completed_at,
        prompt_rendered=service_result.prompt_rendered,
        variables=variables,
        input=input,
        result_text=service_result.result_text,
        result_json=service_result.result_json,
        error=service_result.error,
        finish_reason=service_result.finish_reason,
        prompt_tokens=service_result.prompt_tokens,
        completion_tokens=service_result.completion_tokens,
        total_tokens=service_result.total_tokens,
        cached_tokens=service_result.cached_tokens,
        reasoning_tokens=service_result.reasoning_tokens,
        system_fingerprint=service_result.system_fingerprint,
        provider_response=service_result.provider_response,
    )

    session.add(db_execution)
    await session.commit()
    await session.refresh(db_execution)

    return db_execution


async def list_implementation_executions(
    session: AsyncSession, implementation_id: int
) -> list[ExecutionResult]:
    # Ensure implementation exists
    impl_q = select(Implementation).where(Implementation.id == implementation_id)
    impl_res = await session.execute(impl_q)
    impl = impl_res.scalar_one_or_none()
    if not impl:
        raise NotFoundError(
            f"Implementation with id {implementation_id} not found"
        )

    q = (
        select(ExecutionResult)
        .where(ExecutionResult.implementation_id == implementation_id)
        .order_by(ExecutionResult.created_at.desc())
    )
    res = await session.execute(q)
    executions: Sequence[ExecutionResult] = res.scalars().all()
    return list(executions)


async def list_task_executions(
    session: AsyncSession, task_id: int
) -> list[ExecutionResult]:
    # Ensure task exists
    task_q = select(Task).where(Task.id == task_id)
    task_res = await session.execute(task_q)
    task = task_res.scalar_one_or_none()
    if not task:
        raise NotFoundError(f"Task with id {task_id} not found")

    q = (
        select(ExecutionResult)
        .where(ExecutionResult.task_id == task_id)
        .order_by(ExecutionResult.created_at.desc())
    )
    res = await session.execute(q)
    executions: Sequence[ExecutionResult] = res.scalars().all()
    return list(executions)


async def get_execution(
    session: AsyncSession, execution_id: int
) -> ExecutionResult:
    q = select(ExecutionResult).where(ExecutionResult.id == execution_id)
    res = await session.execute(q)
    execution = res.scalar_one_or_none()
    if not execution:
        raise NotFoundError(f"Execution with id {execution_id} not found")
    return execution


async def list_executions(
    session: AsyncSession,
    task_id: int | None,
    implementation_id: int | None,
) -> list[ExecutionResult]:
    q = select(ExecutionResult)
    if task_id is not None:
        q = q.where(ExecutionResult.task_id == task_id)
    if implementation_id is not None:
        q = q.where(ExecutionResult.implementation_id == implementation_id)
    q = q.order_by(ExecutionResult.created_at.desc())

    res = await session.execute(q)
    executions: Sequence[ExecutionResult] = res.scalars().all()
    return list(executions)


async def delete_execution(session: AsyncSession, execution_id: int) -> None:
    q = select(ExecutionResult).where(ExecutionResult.id == execution_id)
    res = await session.execute(q)
    execution = res.scalar_one_or_none()
    if not execution:
        raise NotFoundError(f"Execution with id {execution_id} not found")
    await session.delete(execution)
    await session.commit()



