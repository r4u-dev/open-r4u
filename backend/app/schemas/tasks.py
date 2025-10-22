"""Task schemas for API requests and responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.traces import Reasoning, ToolDefinition


class ImplementationCreate(BaseModel):
    """Schema for creating an implementation (version)."""

    version: str = "0.1"
    prompt: str
    model: str
    temperature: float | None = None
    reasoning: Reasoning | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    max_output_tokens: int
    temp: bool = False


class ImplementationRead(ImplementationCreate):
    """Schema for reading an implementation."""

    id: int
    task_id: int
    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    """Base schema for task details."""

    path: str | None = None


class TaskCreate(TaskBase):
    """Schema for task creation payload."""

    project: str = "Default Project"  # Project name, defaults to "Default Project"
    implementation: ImplementationCreate  # Initial implementation version


class TaskRead(TaskBase):
    """Schema for task responses."""

    id: int
    project_id: int
    production_version_id: int | None = None
    model_config = ConfigDict(from_attributes=True)
