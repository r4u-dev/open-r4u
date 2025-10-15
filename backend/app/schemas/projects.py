"""Project schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    """Base schema for projects."""

    name: str
    description: str | None = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""


class ProjectRead(ProjectBase):
    """Schema for reading a project."""

    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
