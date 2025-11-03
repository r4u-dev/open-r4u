from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, conlist, validator

from app.enums import OptimizationStatus

# Allowed fields the optimization process may mutate
OptimizationMutableField = Literal[
    "prompt",
    "model",
    "temperature",
    "max_output_tokens",
]


class OptimizationRunRequest(BaseModel):
    task_id: int = Field(..., ge=1)
    max_iterations: int = Field(..., ge=1, le=100)
    changeable_fields: conlist(OptimizationMutableField, min_length=1)
    patience: int = Field(default=3, ge=1, le=20)

    @validator("changeable_fields")
    def ensure_unique_fields(cls, value: list[OptimizationMutableField]) -> list[OptimizationMutableField]:
        if len(value) != len(set(value)):
            raise ValueError("changeable_fields must not contain duplicates")
        return value


class OptimizationIterationGraderDetail(BaseModel):
    score: float | None
    reasonings: list[str] = Field(default_factory=list)


class OptimizationIterationEval(BaseModel):
    implementation_id: int
    version: str | None
    avg_cost: float | None
    avg_execution_time_ms: float | None
    graders: list[OptimizationIterationGraderDetail] = Field(default_factory=list)


class OptimizationIterationDetail(BaseModel):
    iteration: int
    proposed_changes: dict
    candidate_implementation_id: int | None
    evaluation: OptimizationIterationEval | None


# Optimization Database Schemas
class OptimizationBase(BaseModel):
    """Base schema for optimization details."""

    status: OptimizationStatus = Field(OptimizationStatus.PENDING, description="Status of the optimization")
    started_at: datetime | None = Field(None, description="When the optimization started")
    completed_at: datetime | None = Field(None, description="When the optimization completed")
    error: str | None = Field(None, description="Error message if optimization failed")

    # Parameters
    max_iterations: int = Field(..., ge=1, description="Maximum number of iterations")
    changeable_fields: list[str] = Field(..., description="Fields that can be changed during optimization")
    max_consecutive_no_improvements: int = Field(3, ge=1, description="Patience parameter")

    # Progress
    iterations_run: int = Field(0, ge=0, description="Number of iterations completed")
    current_iteration: int | None = Field(None, description="Current iteration in progress")

    # Results
    iterations: list[OptimizationIterationDetail] = Field(default_factory=list, description="Iteration details")


class OptimizationRead(OptimizationBase):
    """Schema for optimization response."""

    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationListItem(BaseModel):
    """Lightweight schema for listing optimizations."""

    id: int
    task_id: int
    status: OptimizationStatus
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    iterations_run: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Dashboard Schemas
class OutperformingVersionItem(BaseModel):
    """Schema for a version that outperforms the production version."""

    task_id: int
    task_name: str
    production_version: str | None = Field(None, description="Production version string")
    optimized_version: str = Field(..., description="Optimized version string")
    production_implementation_id: int | None = Field(None, description="Production implementation ID")
    optimized_implementation_id: int = Field(..., description="Optimized implementation ID")

    # Deltas (changes)
    score_delta: float | None = Field(None, description="Change in final evaluation score")
    quality_delta_percent: float | None = Field(None, description="Percentage change in quality score")
    cost_delta_percent: float | None = Field(None, description="Percentage change in average cost")
    time_delta_ms: float | None = Field(None, description="Change in average execution time in milliseconds")

    # Absolute values for reference
    production_score: float | None = Field(None, description="Production final evaluation score")
    optimized_score: float | None = Field(None, description="Optimized final evaluation score")
    production_quality: float | None = Field(None, description="Production quality score")
    optimized_quality: float | None = Field(None, description="Optimized quality score")
    production_cost: float | None = Field(None, description="Production average cost")
    optimized_cost: float | None = Field(None, description="Optimized average cost")
    production_time_ms: float | None = Field(None, description="Production average execution time in milliseconds")
    optimized_time_ms: float | None = Field(None, description="Optimized average execution time in milliseconds")


class OptimizationDashboardSummary(BaseModel):
    """Summary metrics for the optimization dashboard."""

    score_boost_percent: float | None = Field(None, description="Average percentage boost in final evaluation score")
    quality_boost_percent: float | None = Field(None, description="Average percentage boost in quality score")
    money_saved: float | None = Field(None, description="Total estimated cost savings in dollars")

    # Additional metrics
    total_versions_found: int = Field(0, description="Total number of outperforming versions found")
    total_cost: float | None = Field(None, description="Total cost of optimizations")
    running_count: int = Field(0, description="Number of optimizations currently running")


class OptimizationDashboardResponse(BaseModel):
    """Response schema for optimization dashboard endpoint."""

    summary: OptimizationDashboardSummary
    outperforming_versions: list[OutperformingVersionItem] = Field(
        default_factory=list,
        description="List of implementations that outperform their production versions",
    )
