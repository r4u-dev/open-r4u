"""Optimization models for tracking optimization runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import OptimizationStatus
from app.models.base import Base, created_at_col, intpk, updated_at_col

if TYPE_CHECKING:
    from app.models.tasks import Task

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Optimization(Base):
    """Optimization model for storing optimization run information and progress."""

    __tablename__ = "optimization"
    __table_args__ = (
        Index("ix_optimization_task_id", "task_id"),
        Index("ix_optimization_status", "status"),
        Index("ix_optimization_started_at", "started_at"),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[OptimizationStatus] = mapped_column(
        SQLEnum(OptimizationStatus, name="optimization_status"),
        nullable=False,
        default=OptimizationStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optimization parameters
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    changeable_fields: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    max_consecutive_no_improvements: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    # Progress tracking
    iterations_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_iteration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Iteration details (stored as JSON array, updated incrementally)
    iterations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="optimizations")

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
