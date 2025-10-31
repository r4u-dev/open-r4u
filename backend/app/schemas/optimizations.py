from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, Field, conlist, confloat, validator

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
    score: Optional[float]
    reasonings: List[str] = Field(default_factory=list)


class OptimizationIterationEval(BaseModel):
    implementation_id: int
    version: Optional[str]
    avg_cost: Optional[float]
    avg_execution_time_ms: Optional[float]
    final_score: Optional[float]
    graders: List[OptimizationIterationGraderDetail] = Field(default_factory=list)


class OptimizationIterationDetail(BaseModel):
    iteration: int
    proposed_changes: dict
    candidate_implementation_id: Optional[int]
    evaluation: Optional[OptimizationIterationEval]


# Optimization Database Schemas
class OptimizationBase(BaseModel):
    """Base schema for optimization details."""

    status: OptimizationStatus = Field(OptimizationStatus.PENDING, description="Status of the optimization")
    started_at: datetime | None = Field(None, description="When the optimization started")
    completed_at: datetime | None = Field(None, description="When the optimization completed")
    error: str | None = Field(None, description="Error message if optimization failed")
    
    # Parameters
    max_iterations: int = Field(..., ge=1, description="Maximum number of iterations")
    changeable_fields: List[str] = Field(..., description="Fields that can be changed during optimization")
    max_consecutive_no_improvements: int = Field(3, ge=1, description="Patience parameter")
    
    # Progress
    iterations_run: int = Field(0, ge=0, description="Number of iterations completed")
    current_iteration: int | None = Field(None, description="Current iteration in progress")
    
    # Results
    best_implementation_id: int | None = Field(None, description="ID of the best implementation found")
    best_score: float | None = Field(None, description="Best score achieved")
    iterations: List[OptimizationIterationDetail] = Field(default_factory=list, description="Iteration details")


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
    best_implementation_id: int | None
    best_score: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationSummary(BaseModel):
    """Summary statistics for optimizations."""

    versions_found: int = Field(0, description="Number of optimized implementations that outperform production")
    total_cost: float = Field(0.0, description="Total cost of running optimizations")
    running_count: int = Field(0, description="Number of currently running optimizations")
    score_boost: float | None = Field(None, description="Average score improvement percentage")
    accuracy_boost: float | None = Field(None, description="Average accuracy (quality score) improvement percentage")
    money_saved: float | None = Field(None, description="Total estimated cost savings")


class OutperformingVersion(BaseModel):
    """An implementation version that outperforms production."""

    task_id: int
    task_name: str | None
    production_version: str | None
    optimized_version: str
    implementation_id: int
    score_delta: float | None = Field(None, description="Change in final evaluation score")
    accuracy_delta: float | None = Field(None, description="Change in quality score (accuracy) as percentage")
    cost_delta: float | None = Field(None, description="Change in cost as percentage (negative = savings)")
    time_delta: float | None = Field(None, description="Change in execution time in seconds (negative = faster)")


class OptimizationDashboardResponse(BaseModel):
    """Response schema for optimization dashboard."""

    summary: OptimizationSummary
    outperforming_versions: List[OutperformingVersion]
    error: str | None = Field(None, description="Error message if optimization failed")
    
    # Parameters
    max_iterations: int = Field(..., ge=1, description="Maximum number of iterations")
    changeable_fields: List[str] = Field(..., description="Fields that can be changed during optimization")
    max_consecutive_no_improvements: int = Field(3, ge=1, description="Patience parameter")
    
    # Progress
    iterations_run: int = Field(0, ge=0, description="Number of iterations completed")
    current_iteration: int | None = Field(None, description="Current iteration in progress")
    
    # Results
    best_implementation_id: int | None = Field(None, description="ID of the best implementation found")
    best_score: float | None = Field(None, description="Best score achieved")
    iterations: List[OptimizationIterationDetail] = Field(default_factory=list, description="Iteration details")
