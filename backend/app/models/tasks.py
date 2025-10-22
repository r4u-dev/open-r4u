"""Task model for grouping similar traces."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk, updated_at_col
from app.models.executions import ExecutionResult

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Implementation(Base):
    """Implementation model for storing LLM configuration and parameters (versions of a task)."""

    __tablename__ = "implementation"
    __table_args__ = (
        Index("ix_implementation_task_id", "task_id"),
        Index("ix_implementation_model", "model"),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="0.1")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float | None] = mapped_column(nullable=True)
    reasoning: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    tools: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)
    tool_choice: Mapped[str | dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True,
    )
    response_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True,
    )
    max_output_tokens: Mapped[int] = mapped_column(nullable=False)
    temp: Mapped[bool] = mapped_column(nullable=False, default=False)

    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="implementations",
        foreign_keys=[task_id],
    )  # type: ignore

    executions: Mapped[list["ExecutionResult"]] = relationship(  # type: ignore
        "ExecutionResult",
        back_populates="implementation",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class Task(Base):
    """Task model for grouping similar traces with multiple implementation versions."""

    __tablename__ = "task"
    __table_args__ = (
        Index("ix_task_project_id", "project_id"),
        Index("ix_task_production_version_id", "production_version_id"),
    )

    id: Mapped[intpk]
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("implementation.id", ondelete="SET NULL"),
        nullable=True,
    )

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")  # type: ignore
    implementations: Mapped[list["Implementation"]] = relationship(
        "Implementation",
        back_populates="task",
        foreign_keys="Implementation.task_id",
        cascade="all, delete-orphan",
    )  # type: ignore
    production_version: Mapped["Implementation | None"] = relationship(
        "Implementation",
        foreign_keys=[production_version_id],
        post_update=True,
    )  # type: ignore
    traces: Mapped[list["Trace"]] = relationship(  # type: ignore
        "Trace",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    executions: Mapped[list["ExecutionResult"]] = relationship(  # type: ignore
        "ExecutionResult",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
