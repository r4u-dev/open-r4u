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

    # Raw data (can be hex-encoded strings or bytes)
    request: bytes | str = Field(..., description="Complete raw request bytes or hex-encoded string")
    request_headers: dict[str, str] = Field(..., description="Complete raw request headers")
    response: bytes | str = Field(..., description="Complete raw response bytes or hex-encoded string")
    response_headers: dict[str, str] = Field(..., description="Complete raw response headers")

    # Optional extracted fields for convenience
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(extra="allow")
    
    @field_validator("request", "response", mode="before")
    @classmethod
    def decode_hex_if_needed(cls, v):
        """Decode hex-encoded strings to bytes."""
        if isinstance(v, str):
            try:
                return bytes.fromhex(v)
            except ValueError:
                # If it's not hex, assume it's UTF-8 encoded
                return v.encode("utf-8")
        return v
