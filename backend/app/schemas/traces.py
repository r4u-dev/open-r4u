from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import MessageRole


class MessageBase(BaseModel):
    """Base schema for messages."""

    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a message."""


class MessageRead(MessageBase):
    """Schema for reading a message."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class TraceBase(BaseModel):
    """Base schema for trace details."""

    model: str
    result: str | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime


class TraceCreate(TraceBase):
    """Schema for trace creation payload."""

    messages: list[MessageCreate]


class TraceRead(TraceBase):
    """Schema for trace responses."""

    id: int
    messages: list[MessageRead]
    model_config = ConfigDict(from_attributes=True)