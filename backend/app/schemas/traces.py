from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums import FinishReason, ItemType, MessageRole, ReasoningEffort


# Reasoning Schema
class Reasoning(BaseModel):
    """Schema for reasoning configuration and output."""

    effort: ReasoningEffort | None = None
    summary: Literal["auto", "concise", "detailed"] | None = None
    generate_summary: Literal["auto", "concise", "detailed"] | None = Field(
        default=None,
        deprecated="Use 'summary' instead",
    )
    model_config = ConfigDict(extra="allow")


# Tool and Function Schemas
class FunctionCall(BaseModel):
    """Schema representing a function invocation."""

    name: str
    arguments: str | dict[str, Any]  # Can be JSON string or dict
    model_config = ConfigDict(extra="allow")


class ToolCall(BaseModel):
    """Schema describing an LLM-issued tool call."""

    id: str
    type: str = "function"
    function: FunctionCall
    model_config = ConfigDict(extra="allow")


class FunctionDefinition(BaseModel):
    """Schema for a function definition."""

    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool | None = None
    model_config = ConfigDict(extra="allow")


class ToolDefinition(BaseModel):
    """Schema for a tool definition supplied to the LLM (OpenAI format)."""

    type: str = "function"
    function: FunctionDefinition
    model_config = ConfigDict(extra="allow")


# Input Item Schemas
class MessageItem(BaseModel):
    """Message item in trace input."""

    type: Literal[ItemType.MESSAGE] = ItemType.MESSAGE
    role: MessageRole
    content: Any | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    model_config = ConfigDict(extra="allow")


class FunctionCallItem(BaseModel):
    """Function call item in trace input."""

    type: Literal[ItemType.FUNCTION_CALL] = ItemType.FUNCTION_CALL
    id: str
    name: str
    arguments: str | dict[str, Any]
    model_config = ConfigDict(extra="allow")


class FunctionResultItem(BaseModel):
    """Function result item in trace input."""

    type: Literal[ItemType.FUNCTION_RESULT] = ItemType.FUNCTION_RESULT
    call_id: str
    name: str
    result: Any
    model_config = ConfigDict(extra="allow")


class ToolCallItem(BaseModel):
    """Tool call item in trace input."""

    type: Literal[ItemType.TOOL_CALL] = ItemType.TOOL_CALL
    id: str
    tool_name: str
    arguments: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ToolResultItem(BaseModel):
    """Tool result item in trace input."""

    type: Literal[ItemType.TOOL_RESULT] = ItemType.TOOL_RESULT
    call_id: str
    tool_name: str
    result: Any
    is_error: bool = False
    model_config = ConfigDict(extra="allow")


class MediaItem(BaseModel):
    """Media item (image/video/audio) in trace input."""

    type: Literal[ItemType.IMAGE, ItemType.VIDEO, ItemType.AUDIO]
    url: str | None = None
    data: str | None = None  # Base64 encoded data
    mime_type: str | None = None
    metadata: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class MCPToolCallItem(BaseModel):
    """MCP tool call item in trace input."""

    type: Literal[ItemType.MCP_TOOL_CALL] = ItemType.MCP_TOOL_CALL
    id: str
    server: str
    tool_name: str
    arguments: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class MCPToolResultItem(BaseModel):
    """MCP tool result item in trace input."""

    type: Literal[ItemType.MCP_TOOL_RESULT] = ItemType.MCP_TOOL_RESULT
    call_id: str
    server: str
    tool_name: str
    result: Any
    is_error: bool = False
    model_config = ConfigDict(extra="allow")


# Union type for all input items
InputItem = (
    MessageItem
    | FunctionCallItem
    | FunctionResultItem
    | ToolCallItem
    | ToolResultItem
    | MediaItem
    | MCPToolCallItem
    | MCPToolResultItem
)


# Legacy Message Schemas for backward compatibility during transition
class MessageBase(BaseModel):
    """Base schema for messages (legacy)."""

    role: MessageRole
    content: Any | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    model_config = ConfigDict(extra="allow")


class MessageCreate(MessageBase):
    """Schema for creating a message (legacy)."""


class MessageRead(MessageBase):
    """Schema for reading a message (legacy)."""

    id: int
    model_config = ConfigDict(from_attributes=True, extra="allow")


# Input Item Read Schema
class InputItemRead(BaseModel):
    """Schema for reading an input item."""

    id: int
    type: ItemType
    data: dict[str, Any]
    position: int
    model_config = ConfigDict(from_attributes=True)


class TraceBase(BaseModel):
    """Base schema for trace details."""

    model: str
    result: str | None = None
    error: str | None = None
    path: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    tools: list[ToolDefinition] | None = None
    task_id: int | None = None
    
    # Request parameters
    instructions: str | None = None
    prompt: str | None = None
    temperature: float | None = None
    tool_choice: str | dict[str, Any] | None = None  # "auto", "none", "required", or specific tool
    
    # Token usage
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    
    # Additional usage metrics
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    
    # Completion details
    finish_reason: FinishReason | None = None
    system_fingerprint: str | None = None
    
    # Reasoning attributes
    reasoning: Reasoning | None = None  # Reasoning configuration/output for models that support it
    
    # Schema and metadata
    response_schema: dict[str, Any] | None = None
    trace_metadata: dict[str, Any] | None = None


class TraceCreate(TraceBase):
    """Schema for trace creation payload."""

    input: list[InputItem]  # Replaces messages
    project: str = "Default Project"  # Project name, defaults to "Default Project"
    
    @field_validator("input", mode="before")
    @classmethod
    def validate_input(cls, v):
        """Validate input items."""
        if not isinstance(v, list):
            raise ValueError("input must be a list")
        return v


class TraceRead(TraceBase):
    """Schema for trace responses."""

    id: int
    project_id: int
    input: list[InputItemRead] = Field(default_factory=list, validation_alias="input_items", serialization_alias="input")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)