"""Task schemas for API requests and responses."""

from datetime import datetime
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
    max_output_tokens: int
    temp: bool = False


class ImplementationRead(ImplementationCreate):
    """Schema for reading an implementation."""

    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    """Base schema for task details."""

    path: str | None = None
    response_schema: dict[str, Any] | None = None


class TaskCreate(TaskBase):
    """Schema for task creation payload."""

    name: str | None = None
    description: str | None = None
    project: str = "Default Project"  # Project name, defaults to "Default Project"
    implementation: ImplementationCreate  # Initial implementation version


class TaskSchema(TaskBase):
    """Schema for task responses."""

    id: int
    name: str
    description: str
    project_id: int
    production_version_id: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
