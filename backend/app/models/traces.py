from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import FinishReason, ItemType
from app.models.base import Base, created_at_col, intpk, updated_at_col
from app.models.evaluation import Grade

if TYPE_CHECKING:
    from app.models.http_traces import HTTPTrace
    from app.models.projects import Project
    from app.models.tasks import Implementation


# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Trace(Base):
    """Trace model capturing LLM execution metadata and input history."""

    __tablename__ = "trace"
    __table_args__ = (
        Index("ix_trace_started_at", "started_at"),
        Index("ix_trace_model", "model"),
        Index("ix_trace_project_id", "project_id"),
        Index("ix_trace_implementation_id", "implementation_id"),
        Index("ix_trace_finish_reason", "finish_reason"),
    )

    id: Mapped[intpk]
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    implementation_id: Mapped[int | None] = mapped_column(
        ForeignKey("implementation.id", ondelete="SET NULL"),
        nullable=True,
    )
    http_trace_id: Mapped[int | None] = mapped_column(
        ForeignKey("http_trace.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Request parameters
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_choice: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Token usage
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Completion details
    finish_reason: Mapped[FinishReason | None] = mapped_column(
        SQLEnum(FinishReason, name="finish_reason"),
        nullable=True,
    )
    system_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reasoning: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    # Schema and metadata
    response_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    trace_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Prompt placeholder variables (for matching with implementation templates)
    prompt_variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    project: Mapped["Project"] = relationship("Project", back_populates="traces")  # type: ignore
    implementation: Mapped["Implementation | None"] = relationship(
        "Implementation",
        back_populates="traces",
    )  # type: ignore
    http_trace: Mapped["HTTPTrace | None"] = relationship(
        "HTTPTrace",
        back_populates="trace",
    )  # type: ignore
    input_items: Mapped[list["TraceInputItem"]] = relationship(
        "TraceInputItem",
        back_populates="trace",
        cascade="all, delete-orphan",
        order_by="TraceInputItem.position",
    )
    tools: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)
    grades: Mapped[list["Grade"]] = relationship(
        "Grade",
        foreign_keys="Grade.trace_id",
        back_populates="trace",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class TraceInputItem(Base):
    """Individual input item belonging to a trace."""

    __tablename__ = "trace_input_item"
    __table_args__ = (
        Index(
            "ix_trace_input_item_trace_id_position",
            "trace_id",
            "position",
            unique=True,
        ),
        Index("ix_trace_input_item_type", "type"),
    )

    id: Mapped[intpk]
    trace_id: Mapped[int] = mapped_column(
        ForeignKey("trace.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ItemType] = mapped_column(
        SQLEnum(ItemType, name="item_type"),
        nullable=False,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    trace: Mapped[Trace] = relationship("Trace", back_populates="input_items")

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
