from __future__ import annotations

from typing import Literal, Optional, List

from pydantic import BaseModel, Field, conlist, confloat, validator


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


class OptimizationResult(BaseModel):
    """Internal/result contract returned by OptimizationService.run."""

    best_implementation_id: Optional[int]
    best_score: Optional[float]
    iterations_run: int
    iterations: List["OptimizationIterationDetail"] = Field(default_factory=list)


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

