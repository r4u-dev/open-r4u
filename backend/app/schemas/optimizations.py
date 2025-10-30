from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, conlist, confloat, validator


# Allowed fields the optimization process may mutate
OptimizationMutableField = Literal[
    "prompt",
    "model",
    "temperature",
    "tools",
    "tool_choice",
    "max_output_tokens",
    "reasoning",
]


class OptimizationRunRequest(BaseModel):
    task_id: int = Field(..., ge=1)
    max_iterations: int = Field(..., ge=1, le=100)
    variants_per_iter: int = Field(..., ge=1, le=50)
    changeable_fields: conlist(OptimizationMutableField, min_length=1)
    improvement_threshold: confloat(ge=0.0, le=1.0) = 0.01

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
