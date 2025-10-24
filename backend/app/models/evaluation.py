"""Evaluation models for grader and grade system."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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

from app.enums import ScoreType, EvaluationStatus
from app.models.base import Base, created_at_col, intpk, updated_at_col

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Grader(Base):
    """Grader model for storing LLM-based evaluation configurations."""

    __tablename__ = "grader"
    __table_args__ = (
        Index("ix_grader_project_id", "project_id"),
        Index("ix_grader_name", "name"),
        Index("ix_grader_is_active", "is_active"),
    )

    id: Mapped[intpk]
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    score_type: Mapped[ScoreType] = mapped_column(
        SQLEnum(ScoreType, name="score_type"),
        nullable=False,
    )

    # Full LLM configuration
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    response_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="graders")  # type: ignore
    grades: Mapped[list["Grade"]] = relationship(
        "Grade",
        back_populates="grader",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class Grade(Base):
    """Grade model for storing evaluation results of traces and execution results."""

    __tablename__ = "grade"
    __table_args__ = (
        Index("ix_grade_grader_id", "grader_id"),
        Index("ix_grade_trace_id", "trace_id"),
        Index("ix_grade_execution_result_id", "execution_result_id"),
        Index("ix_grade_grading_started_at", "grading_started_at"),
        # Ensure exactly one target is specified
        CheckConstraint(
            "(trace_id IS NULL) != (execution_result_id IS NULL)",
            name="ck_grade_exactly_one_target",
        ),
    )

    id: Mapped[intpk]
    grader_id: Mapped[int] = mapped_column(
        ForeignKey("grader.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Polymorphic target: either trace_id OR execution_result_id
    trace_id: Mapped[int | None] = mapped_column(
        ForeignKey("trace.id", ondelete="CASCADE"),
        nullable=True,
    )
    execution_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("execution_result.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Score results
    score_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Grader LLM metadata
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    grader_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    # Execution metadata
    grading_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    grading_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    grader: Mapped["Grader"] = relationship("Grader", back_populates="grades")
    trace: Mapped["Trace | None"] = relationship("Trace", back_populates="grades")  # type: ignore
    execution_result: Mapped["ExecutionResult | None"] = relationship("ExecutionResult", back_populates="grades")  # type: ignore

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class TestCase(Base):
    """Test case model for storing test inputs and expected outputs for tasks."""

    __test__ = False

    __tablename__ = "test_case"
    __table_args__ = (
        Index("ix_test_case_task_id", "task_id"),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    arguments: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="test_cases")  # type: ignore

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class EvaluationConfig(Base):
    """Evaluation configuration model for storing task-level evaluation settings."""

    __tablename__ = "evaluation_config"
    __table_args__ = (
        Index("ix_evaluation_config_task_id", "task_id"),
        # Ensure one config per task
        CheckConstraint(
            "task_id IS NOT NULL",
            name="ck_evaluation_config_task_id_not_null",
        ),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    quality_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    cost_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    time_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    grader_ids: Mapped[list[int]] = mapped_column(JSONType, nullable=False, default=list)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="evaluation_config")  # type: ignore

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class Evaluation(Base):
    """Evaluation model for storing evaluation run information and metrics."""

    __tablename__ = "evaluation"
    __table_args__ = (
        Index("ix_evaluation_implementation_id", "implementation_id"),
        Index("ix_evaluation_task_id", "task_id"),
        Index("ix_evaluation_status", "status"),
        Index("ix_evaluation_started_at", "started_at"),
    )

    id: Mapped[intpk]
    implementation_id: Mapped[int] = mapped_column(
        ForeignKey("implementation.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, name="evaluation_status"),
        nullable=False,
        default=EvaluationStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    test_case_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics fields (stored)
    grader_scores: Mapped[dict[str, float]] = mapped_column(JSONType, nullable=False, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Efficiency and final scores are calculated on-demand, not stored

    # Relationships
    implementation: Mapped["Implementation"] = relationship("Implementation", back_populates="evaluations")  # type: ignore
    task: Mapped["Task"] = relationship("Task", back_populates="evaluations")  # type: ignore

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]


class TargetTaskMetrics(Base):
    """Target task metrics model for storing best-known values for efficiency score calculation."""

    __tablename__ = "target_task_metrics"
    __table_args__ = (
        Index("ix_target_task_metrics_task_id", "task_id"),
        Index("ix_target_task_metrics_last_updated", "last_updated_at"),
    )

    id: Mapped[intpk]
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="target_task_metrics")  # type: ignore

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
