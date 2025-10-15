from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.enums import MessageRole


class ToolFunctionCall(BaseModel):
    """Schema representing a tool function invocation."""

    name: str
    arguments: Any
    model_config = ConfigDict(extra="allow")


class ToolCall(BaseModel):
    """Schema describing an LLM-issued tool call."""

    id: str | None = None
    type: str | None = None
    function: ToolFunctionCall | None = None
    model_config = ConfigDict(extra="allow")


class ToolDefinition(BaseModel):
    """Schema for a tool definition supplied to the LLM."""

    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = Field(default=None, alias="schema")
    type: str | None = None
    metadata: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)


class MessageBase(BaseModel):
    """Base schema for messages."""

    role: MessageRole
    content: Any | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    model_config = ConfigDict(extra="allow")


class MessageCreate(MessageBase):
    """Schema for creating a message."""


class MessageRead(MessageBase):
    """Schema for reading a message."""

    id: int
    model_config = ConfigDict(from_attributes=True, extra="allow")


class TraceBase(BaseModel):
    """Base schema for trace details."""

    model: str
    result: str | None = None
    error: str | None = None
    path: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    tools: list[ToolDefinition] | None = None


class TraceCreate(TraceBase):
    """Schema for trace creation payload."""

    messages: list[MessageCreate]
    project: str = "Default Project"  # Project name, defaults to "Default Project"


class TraceRead(TraceBase):
    """Schema for trace responses."""

    id: int
    project_id: int
    messages: list[MessageRead]
    model_config = ConfigDict(from_attributes=True)