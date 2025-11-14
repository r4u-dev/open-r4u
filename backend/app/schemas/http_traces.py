"""Schemas for HTTP-level trace ingestion."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HTTPTraceCreate(BaseModel):
    """Schema for HTTP trace creation (provider-agnostic)."""

    # Timing
    started_at: datetime = Field(..., description="When the request started")
    completed_at: datetime = Field(..., description="When the request completed")

    # Status
    status_code: int = Field(..., description="HTTP status code")
    error: str | None = Field(None, description="Error message if any")
    path: str | None = Field(
        None,
        description="The call path where the request was made",
    )

    # Raw data (accepts bytes or strings, stored as strings)
    request: bytes | str = Field(
        ...,
        description="Complete raw request as bytes or string",
    )
    request_headers: dict[str, str] = Field(
        ...,
        description="Complete raw request headers",
    )
    response: bytes | str = Field(
        ...,
        description="Complete raw response as bytes or string",
    )
    response_headers: dict[str, str] = Field(
        ...,
        description="Complete raw response headers",
    )

    # Optional extracted fields for convenience
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("request", "response", mode="before")
    @classmethod
    def convert_to_string(cls, v):
        """Convert bytes or hex-encoded strings to string."""
        if isinstance(v, str):
            # Try to decode as hex first
            try:
                decoded_bytes = bytes.fromhex(v)
                return decoded_bytes.decode("utf-8", errors="replace")
            except (ValueError, AttributeError):
                # Not hex-encoded, return as-is
                return v
        elif isinstance(v, bytes):
            return v.decode("utf-8", errors="replace")
        return v


class HTTPTraceRead(BaseModel):
    """Schema for reading HTTP trace data."""

    id: int
