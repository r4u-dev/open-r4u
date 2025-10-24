from enum import Enum


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"


class ItemType(str, Enum):
    """Type of item in trace input."""

    MESSAGE = "message"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MCP_TOOL_CALL = "mcp_tool_call"
    MCP_TOOL_RESULT = "mcp_tool_result"


class FinishReason(str, Enum):
    """Reason why the model stopped generating."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    FUNCTION_CALL = "function_call"
    ERROR = "error"


class ReasoningEffort(str, Enum):
    """Reasoning effort level for reasoning models."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScoreType(str, Enum):
    """Type of score for grader evaluation."""

    FLOAT = "float"  # 0.0 - 1.0 numeric scores
    BOOLEAN = "boolean"  # true/false binary evaluation


class EvaluationStatus(str, Enum):
    """Status of an evaluation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
