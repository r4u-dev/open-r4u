"""Execution schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.enums import FinishReason
from app.schemas.traces import InputItem


class ExecutionRequest(BaseModel):
    """Schema for task execution request."""

    # Variables to render the prompt template
    variables: dict[str, Any] | None = None
    
    # Optional message history (alternative to simple prompt rendering)
    input: list[InputItem] | None = None
    
    # Optional overrides for implementation parameters
    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    reasoning: dict[str, Any] | None = None


class ExecutionResultBase(BaseModel):
    """Base schema for execution result."""

    task_id: int
    implementation_id: int
    started_at: datetime
    completed_at: datetime | None = None
    prompt_rendered: str
    variables: dict[str, Any] | None = None
    input: list[InputItem] | None = None
    result_text: str | None = None
    result_json: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    error: str | None = None
    finish_reason: FinishReason | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    system_fingerprint: str | None = None


class ExecutionResultRead(ExecutionResultBase):
    """Schema for execution result response."""

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

