from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.enums import (
    FinishReason,
    ItemType,
    MessageRole,
    ReasoningEffort,
)
from app.services.pricing_service import PricingService


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


# Output Item Schemas (OpenAI Responses API compatible)
class OutputMessageContent(BaseModel):
    """Content within an output message."""

    type: str
    text: str | None = None
    model_config = ConfigDict(extra="allow")


class OutputMessageItem(BaseModel):
    """Output message from the assistant."""

    type: Literal["message"] = "message"
    id: str
    role: Literal["assistant"] = "assistant"
    content: list[OutputMessageContent] | None = None
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    model_config = ConfigDict(extra="allow")


class FileSearchResult(BaseModel):
    """Result from file search."""

    file_id: str
    text: str | None = None
    filename: str | None = None
    score: float | None = None
    model_config = ConfigDict(extra="allow")


class FileSearchToolCallItem(BaseModel):
    """File search tool call output."""

    type: Literal["file_search_call"] = "file_search_call"
    id: str
    status: Literal["in_progress", "searching", "completed", "incomplete", "failed"]
    queries: list[str] | None = None
    results: list[FileSearchResult] | None = None
    model_config = ConfigDict(extra="allow")


class FunctionToolCallItem(BaseModel):
    """Function tool call output."""

    type: Literal["function_call"] = "function_call"
    id: str
    call_id: str
    name: str
    arguments: str
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    model_config = ConfigDict(extra="allow")


class WebSearchAction(BaseModel):
    """Web search action details."""

    type: str
    model_config = ConfigDict(extra="allow")


class WebSearchToolCallItem(BaseModel):
    """Web search tool call output."""

    type: Literal["web_search_call"] = "web_search_call"
    id: str
    status: Literal["in_progress", "searching", "completed", "failed"]
    action: WebSearchAction | None = None
    model_config = ConfigDict(extra="allow")


class ComputerAction(BaseModel):
    """Computer use action details."""

    type: str
    model_config = ConfigDict(extra="allow")


class ComputerToolCallItem(BaseModel):
    """Computer tool call output."""

    type: Literal["computer_call"] = "computer_call"
    id: str
    call_id: str
    action: ComputerAction | None = None
    pending_safety_checks: list[Any] | None = None
    status: Literal["in_progress", "completed", "incomplete"]
    model_config = ConfigDict(extra="allow")


class ReasoningSummary(BaseModel):
    """Reasoning summary content."""

    type: str | None = None
    text: str | None = None
    model_config = ConfigDict(extra="allow")


class ReasoningContent(BaseModel):
    """Reasoning text content."""

    type: str | None = None
    text: str | None = None
    model_config = ConfigDict(extra="allow")


class ReasoningOutputItem(BaseModel):
    """Reasoning item from the model."""

    type: Literal["reasoning"] = "reasoning"
    id: str
    encrypted_content: str | None = None
    summary: list[ReasoningSummary] | None = None
    content: list[ReasoningContent] | None = None
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    model_config = ConfigDict(extra="allow")


class ImageGenToolCallItem(BaseModel):
    """Image generation tool call output."""

    type: Literal["image_generation_call"] = "image_generation_call"
    id: str
    status: Literal["in_progress", "completed", "generating", "failed"]
    result: str | None = None  # Base64 encoded image
    model_config = ConfigDict(extra="allow")


class CodeInterpreterOutput(BaseModel):
    """Code interpreter output (logs or images)."""

    type: str
    model_config = ConfigDict(extra="allow")


class CodeInterpreterToolCallItem(BaseModel):
    """Code interpreter tool call output."""

    type: Literal["code_interpreter_call"] = "code_interpreter_call"
    id: str
    status: Literal["in_progress", "completed", "incomplete", "interpreting", "failed"]
    container_id: str
    code: str | None = None
    outputs: list[CodeInterpreterOutput] | None = None
    model_config = ConfigDict(extra="allow")


class LocalShellAction(BaseModel):
    """Local shell execution action."""

    type: str | None = None
    command: str | None = None
    model_config = ConfigDict(extra="allow")


class LocalShellToolCallItem(BaseModel):
    """Local shell tool call output."""

    type: Literal["local_shell_call"] = "local_shell_call"
    id: str
    call_id: str
    action: LocalShellAction | None = None
    status: Literal["in_progress", "completed", "incomplete"]
    model_config = ConfigDict(extra="allow")


class MCPToolCallItem(BaseModel):
    """MCP tool call output."""

    type: Literal["mcp_call"] = "mcp_call"
    id: str
    server_label: str
    name: str
    arguments: str
    output: str | None = None
    error: str | None = None
    status: str | None = None
    approval_request_id: str | None = None
    model_config = ConfigDict(extra="allow")


class MCPListToolsTool(BaseModel):
    """Tool available on MCP server."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class MCPListToolsItem(BaseModel):
    """MCP list tools output."""

    type: Literal["mcp_list_tools"] = "mcp_list_tools"
    id: str
    server_label: str
    tools: list[MCPListToolsTool] | None = None
    error: str | None = None
    model_config = ConfigDict(extra="allow")


class MCPApprovalRequestItem(BaseModel):
    """MCP approval request output."""

    type: Literal["mcp_approval_request"] = "mcp_approval_request"
    id: str
    server_label: str
    name: str
    arguments: str
    model_config = ConfigDict(extra="allow")


class CustomToolCallItem(BaseModel):
    """Custom tool call output."""

    type: Literal["custom_tool_call"] = "custom_tool_call"
    id: str
    call_id: str
    name: str
    input: str
    model_config = ConfigDict(extra="allow")


# Union type for all output items
OutputItem = (
    OutputMessageItem
    | FileSearchToolCallItem
    | FunctionToolCallItem
    | WebSearchToolCallItem
    | ComputerToolCallItem
    | ReasoningOutputItem
    | ImageGenToolCallItem
    | CodeInterpreterToolCallItem
    | LocalShellToolCallItem
    | MCPToolCallItem
    | MCPListToolsItem
    | MCPApprovalRequestItem
    | CustomToolCallItem
)


# Input/Output Item Read Schemas
class InputItemRead(BaseModel):
    """Schema for reading an input item."""

    id: int
    type: ItemType
    data: dict[str, Any]
    position: int
    model_config = ConfigDict(from_attributes=True)


class OutputItemRead(BaseModel):
    """Schema for reading an output item."""

    id: int
    type: str
    data: dict[str, Any]
    position: int
    model_config = ConfigDict(from_attributes=True)


class TraceBase(BaseModel):
    """Base schema for trace details."""

    model: str
    error: str | None = None
    path: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    tools: list[ToolDefinition] | None = None
    implementation_id: int | None = None

    # Request parameters
    instructions: str | None = None
    prompt: str | None = None
    temperature: float | None = None
    tool_choice: str | dict[str, Any] | None = (
        None  # "auto", "none", "required", or specific tool
    )

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
    reasoning: Reasoning | None = (
        None  # Reasoning configuration/output for models that support it
    )

    # Schema and metadata
    response_schema: dict[str, Any] | None = None
    trace_metadata: dict[str, Any] | None = None

    # Prompt placeholder variables (for matching with implementation templates)
    prompt_variables: dict[str, Any] | None = None
    max_tokens: int | None = None


class TraceCreate(TraceBase):
    """Schema for trace creation payload."""

    input: list[InputItem] = Field(default_factory=list)
    output: list[OutputItem] = Field(default_factory=list)
    project: str = "Default Project"  # Project name, defaults to "Default Project"


class TraceRead(TraceBase):
    """Schema for trace responses."""

    id: int
    project_id: int
    input: list[InputItemRead] = Field(
        default_factory=list,
        validation_alias="input_items",
        serialization_alias="input",
    )
    output: list[OutputItemRead] = Field(
        default_factory=list,
        validation_alias="output_items",
        serialization_alias="output",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def cost(self) -> float | None:
        """Compute cost from token usage if available."""
        pricing_service = PricingService()
        return pricing_service.calculate_cost(
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            cached_tokens=self.cached_tokens,
        )
