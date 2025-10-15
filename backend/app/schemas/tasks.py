"""Task schemas for API requests and responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.traces import ToolDefinition


class TaskBase(BaseModel):
    """Base schema for task details."""

    prompt: str
    tools: list[ToolDefinition] | None = None
    model: str
    response_schema: dict[str, Any] | None = None


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

    prompt: str | None = None
    tools: list[ToolDefinition] | None = None
    model: str | None = None
    response_schema: dict[str, Any] | None = None
