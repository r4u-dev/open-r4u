"""Evaluation schemas for grader and grade API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums import GradeType


# Grader Schemas
class GraderBase(BaseModel):
    """Base schema for grader details."""

    name: str = Field(..., max_length=255, description="Name of the grader (e.g., 'accuracy', 'toxicity')")
    description: str | None = Field(None, description="Optional description of what this grader evaluates")
    prompt: str = Field(..., description="The LLM prompt used for evaluation")
    grade_type: GradeType = Field(..., description="Type of grade this grader produces")
    
    # LLM configuration
    model: str = Field(..., max_length=255, description="LLM model to use for grading")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature for LLM")
    reasoning: dict[str, Any] | None = Field(None, description="Reasoning configuration for reasoning models")
    response_schema: dict[str, Any] | None = Field(None, description="JSON schema for structured responses")
    max_output_tokens: int = Field(..., gt=0, description="Maximum output tokens")
    
    # Metadata
    is_active: bool = Field(True, description="Whether this grader is active")


class GraderCreate(GraderBase):
    """Schema for creating a grader."""
    pass


class GraderUpdate(BaseModel):
    """Schema for updating a grader (all fields optional)."""

    name: str | None = Field(None, max_length=255)
    description: str | None = None
    prompt: str | None = None
    grade_type: GradeType | None = None
    model: str | None = Field(None, max_length=255)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    reasoning: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    max_output_tokens: int | None = Field(None, gt=0)
    is_active: bool | None = None


class GraderRead(GraderBase):
    """Schema for grader response."""

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    grade_count: int = Field(0, description="Number of grades produced by this grader")

    model_config = ConfigDict(from_attributes=True)


class GraderListItem(BaseModel):
    """Lightweight schema for listing graders."""

    id: int
    project_id: int
    name: str
    description: str | None
    grade_type: GradeType
    is_active: bool
    created_at: datetime
    grade_count: int = Field(0, description="Number of grades produced by this grader")

    model_config = ConfigDict(from_attributes=True)


# Grade Schemas
class GradeBase(BaseModel):
    """Base schema for grade details."""

    # Score results
    score_float: float | None = Field(None, ge=0.0, le=1.0, description="Float score (0.0 - 1.0)")
    score_boolean: bool | None = Field(None, description="Boolean score")
    
    # Grader LLM metadata
    reasoning: str | None = Field(None, description="Explanation from the grader")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score (0.0 - 1.0)")
    grader_response: dict[str, Any] | None = Field(None, description="Raw LLM response")
    
    # Execution metadata
    grading_started_at: datetime
    grading_completed_at: datetime | None = None
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    system_fingerprint: str | None = None


class GradeTargetRequest(BaseModel):
    """Request schema for creating a grade (specifies target)."""

    trace_id: int | None = None
    execution_result_id: int | None = None

    @field_validator("trace_id", "execution_result_id")
    @classmethod
    def validate_exactly_one_target(cls, v, info):
        """Ensure exactly one target is specified."""
        values = info.data
        trace_id = values.get("trace_id")
        execution_result_id = values.get("execution_result_id")
        
        # If we're validating execution_result_id and trace_id is already set
        if info.field_name == "execution_result_id" and trace_id is not None and v is not None:
            raise ValueError("Specify exactly one of trace_id or execution_result_id")
        
        # Final validation: ensure at least one is set
        if info.field_name == "execution_result_id":
            if trace_id is None and v is None:
                raise ValueError("Must specify either trace_id or execution_result_id")
        
        return v


class GradeCreate(GradeBase):
    """Schema for creating a grade (internal use)."""

    grader_id: int
    trace_id: int | None = None
    execution_result_id: int | None = None


class GradeRead(GradeBase):
    """Schema for grade response."""

    id: int
    grader_id: int
    trace_id: int | None
    execution_result_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GradeListItem(BaseModel):
    """Lightweight schema for listing grades."""

    id: int
    grader_id: int
    trace_id: int | None
    execution_result_id: int | None
    score_float: float | None
    score_boolean: bool | None
    grading_started_at: datetime
    grading_completed_at: datetime | None
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

