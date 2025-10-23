"""HTTPTrace model for storing raw HTTP request/response data."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk, updated_at_col

if TYPE_CHECKING:
    from app.models.traces import Trace

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class HTTPTrace(Base):
    """HTTPTrace model capturing raw HTTP request/response data."""

    __tablename__ = "http_trace"
    __table_args__ = (
        Index("ix_http_trace_started_at", "started_at"),
        Index("ix_http_trace_status_code", "status_code"),
    )

    id: Mapped[intpk]

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Status
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw data stored as strings
    request: Mapped[str] = mapped_column(Text, nullable=False)
    request_headers: Mapped[dict[str, str]] = mapped_column(JSONType, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    response_headers: Mapped[dict[str, str]] = mapped_column(JSONType, nullable=False)

    # Metadata
    http_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default={},
    )

    # Relationship to Trace (one-to-one)
    trace: Mapped["Trace | None"] = relationship(
        "Trace",
        back_populates="http_trace",
        uselist=False,
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
