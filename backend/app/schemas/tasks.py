"""Task schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.schemas.traces import Reasoning, ToolDefinition

settings = get_settings()


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


class ImplementationUpdate(BaseModel):
    """Schema for updating an implementation (version)."""

    prompt: str | None = None


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

    name: str | None = Field(default=None, max_length=settings.max_task_name_length)
    description: str | None = Field(
        default=None,
        max_length=settings.max_task_description_length,
    )
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
    cost_percentile: float | None = None
    latency_percentile: float | None = None
    last_activity: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
