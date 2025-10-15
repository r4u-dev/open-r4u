"""Task model for grouping similar traces."""

from typing import Any

from app.models.base import Base, created_at_col, intpk, updated_at_col
from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Task(Base):
    """Task model for grouping similar traces based on prompt, tools, model, and response schema."""

    __tablename__ = "task"
    __table_args__ = (
        Index("ix_task_project_id", "project_id"),
        Index("ix_task_model", "model"),
    )

    id: Mapped[intpk]
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    response_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")  # type: ignore
    traces: Mapped[list["Trace"]] = relationship(  # type: ignore
        "Trace",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
