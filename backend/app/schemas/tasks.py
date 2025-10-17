"""Task schemas for API requests and responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.traces import Reasoning, ToolDefinition


class TaskBase(BaseModel):
    """Base schema for task details."""

    path: str | None = None
    prompt: str
    tools: list[ToolDefinition] | None = None
    model: str
    response_schema: dict[str, Any] | None = None
    
    # Request parameters (matching traces)
    instructions: str | None = None
    temperature: float | None = None
    tool_choice: str | dict[str, Any] | None = None  # "auto", "none", "required", or specific tool
    
    # Reasoning attributes (matching traces)
    reasoning: Reasoning | None = None  # Reasoning configuration for models that support it


class TaskCreate(TaskBase):
    """Schema for task creation payload."""

    project: str = "Default Project"  # Project name, defaults to "Default Project"


class TaskRead(TaskBase):
    """Schema for task responses."""

    id: int
    project_id: int
    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """Schema for task update payload."""

    path: str | None = None
    prompt: str | None = None
    tools: list[ToolDefinition] | None = None
    model: str | None = None
    response_schema: dict[str, Any] | None = None
    
    # Request parameters (matching traces)
    instructions: str | None = None
    temperature: float | None = None
    tool_choice: str | dict[str, Any] | None = None
    
    # Reasoning attributes (matching traces)
    reasoning: Reasoning | None = None
