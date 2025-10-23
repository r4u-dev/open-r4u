"""Execution models for task execution results."""

from datetime import datetime
from typing import Any

from app.enums import FinishReason
from app.models.base import Base, created_at_col, intpk, updated_at_col

from app.models.evaluation import Grade
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class ExecutionResult(Base):
    """Execution result model for storing task execution outputs."""

    __tablename__ = "execution_result"
    __table_args__ = (
        Index("ix_execution_result_task_id", "task_id"),
        Index("ix_execution_result_implementation_id", "implementation_id"),
        Index("ix_execution_result_created_at", "created_at"),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    implementation_id: Mapped[int] = mapped_column(
        ForeignKey("implementation.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Prompt rendering
    prompt_rendered: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    input: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)

    # Results
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution metadata
    finish_reason: Mapped[FinishReason | None] = mapped_column(
        SQLEnum(FinishReason), nullable=True
    )
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(nullable=True)
    system_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Raw provider response for debugging
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task")  # type: ignore
    implementation: Mapped["Implementation"] = relationship("Implementation")  # type: ignore
    grades: Mapped[list["Grade"]] = relationship(
        "Grade",
        foreign_keys="Grade.execution_result_id",
        back_populates="execution_result",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
