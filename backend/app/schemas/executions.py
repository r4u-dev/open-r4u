"""Execution schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.enums import FinishReason


class ExecutionRequest(BaseModel):
    """Schema for task execution request."""

    # Either task_id OR implementation_id must be provided
    task_id: int | None = None
    implementation_id: int | None = None

    # Arguments for task execution - includes variables for prompt rendering and messages
    arguments: dict[str, Any] | None = None

    # Optional overrides for implementation parameters (only for task_id executions)
    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    reasoning: dict[str, Any] | None = None


class ExecutionResultBase(BaseModel):
    """Base schema for execution result with core execution data."""

    # Core execution data
    started_at: datetime
    completed_at: datetime | None = None
    prompt_rendered: str

    # Results
    result_text: str | None = None
    result_json: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    error: str | None = None

    # Execution metadata
    finish_reason: FinishReason | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost: float | None = None
    system_fingerprint: str | None = None
    provider_response: dict[str, Any] | None = None


class ExecutionResultCreate(ExecutionResultBase):
    """Schema for creating execution results (includes task/implementation context)."""

    task_id: int
    implementation_id: int
    arguments: dict[str, Any] | None = None


class ExecutionResultRead(ExecutionResultCreate):
    """Schema for execution result response (includes database fields)."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionResultListItem(BaseModel):
    """Lightweight schema for listing execution results."""

    id: int
    task_id: int
    implementation_id: int
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    finish_reason: FinishReason | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

