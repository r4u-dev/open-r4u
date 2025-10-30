"""Evaluation schemas for grader and grade API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums import ScoreType, EvaluationStatus


# Grader Schemas
class GraderBase(BaseModel):
    """Base schema for grader details."""

    name: str = Field(..., max_length=255, description="Name of the grader (e.g., 'accuracy', 'toxicity')")
    description: str | None = Field(None, description="Optional description of what this grader evaluates")
    prompt: str = Field(..., description="The LLM prompt used for evaluation")
    score_type: ScoreType = Field(..., description="Type of score this grader produces")
    
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
    project_id: int = Field(..., description="ID of the project this grader belongs to")


class GraderUpdate(BaseModel):
    """Schema for updating a grader (all fields optional)."""

    name: str | None = Field(None, max_length=255)
    description: str | None = None
    prompt: str | None = None
    score_type: ScoreType | None = None
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

    model_config = ConfigDict(from_attributes=True)


class GraderListItem(BaseModel):
    """Lightweight schema for listing graders."""

    id: int
    project_id: int
    name: str
    description: str | None
    score_type: ScoreType
    is_active: bool
    created_at: datetime

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

    grader_id: int = Field(..., description="ID of the grader to use")
    trace_id: int | None = None
    execution_result_id: int | None = None
    test_case_id: int | None = None

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
    reasoning: str | None
    confidence: float | None
    grading_started_at: datetime
    grading_completed_at: datetime | None
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Test Case Schemas
class TestCaseBase(BaseModel):
    """Base schema for test case details."""

    __test__ = False
    description: str | None = Field(None, max_length=500, description="Optional description of the test case")
    arguments: dict[str, Any] | None = Field(None, description="Arguments containing variables for prompt rendering and optional 'messages' key")
    expected_output: str = Field(..., description="Expected output for accuracy comparison (JSON stored as string)")


class TestCaseCreate(TestCaseBase):
    """Schema for creating a test case."""

    __test__ = False

    task_id: int = Field(..., description="ID of the task this test case belongs to")


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case (all fields optional)."""

    __test__ = False

    description: str | None = Field(None, max_length=500)
    arguments: dict[str, Any] | None = None
    expected_output: str | None = None


class TestCaseRead(TestCaseBase):
    """Schema for test case response."""

    __test__ = False

    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCaseListItem(BaseModel):
    """Lightweight schema for listing test cases."""

    __test__ = False

    id: int
    task_id: int
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Evaluation Config Schemas
class EvaluationConfigBase(BaseModel):
    """Base schema for evaluation configuration."""

    quality_weight: float = Field(0.5, ge=0.0, le=1.0, description="Weight for quality score (0.0 - 1.0)")
    cost_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for cost efficiency score (0.0 - 1.0)")
    time_weight: float = Field(0.2, ge=0.0, le=1.0, description="Weight for time efficiency score (0.0 - 1.0)")
    grader_ids: list[int] = Field(default_factory=list, description="List of grader IDs to use for evaluation")

    @field_validator("quality_weight", "cost_weight", "time_weight")
    @classmethod
    def validate_weights_sum_to_one(cls, v, info):
        """Ensure weights sum to approximately 1.0."""
        if info.field_name == "time_weight":  # Only validate on the last field
            values = info.data
            total = values.get("quality_weight", 0) + values.get("cost_weight", 0) + v
            if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                raise ValueError("Quality, cost, and time weights must sum to 1.0")
        return v


class EvaluationConfigCreate(EvaluationConfigBase):
    """Schema for creating evaluation configuration."""
    pass


class EvaluationConfigUpdate(BaseModel):
    """Schema for updating evaluation configuration (all fields optional)."""

    quality_weight: float | None = Field(None, ge=0.0, le=1.0)
    cost_weight: float | None = Field(None, ge=0.0, le=1.0)
    time_weight: float | None = Field(None, ge=0.0, le=1.0)
    grader_ids: list[int] | None = None


class EvaluationConfigRead(EvaluationConfigBase):
    """Schema for evaluation configuration response."""

    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Evaluation Schemas
class EvaluationBase(BaseModel):
    """Base schema for evaluation details."""

    status: EvaluationStatus = Field(EvaluationStatus.PENDING, description="Status of the evaluation")
    started_at: datetime | None = Field(None, description="When the evaluation started")
    completed_at: datetime | None = Field(None, description="When the evaluation completed")
    test_case_count: int | None = Field(None, description="Number of test cases executed")
    error: str | None = Field(None, description="Error message if evaluation failed")

    # Metrics fields
    grader_scores: dict[str, float] = Field(default_factory=dict, description="Average score per grader")
    quality_score: float | None = Field(None, ge=0.0, le=1.0, description="Overall quality score (average of all grader scores)")
    avg_cost: float | None = Field(None, ge=0.0, description="Average cost across all test executions")
    avg_execution_time_ms: float | None = Field(None, ge=0.0, description="Average execution time in milliseconds")
    cost_efficiency_score: float | None = Field(None, ge=0.0, le=1.0, description="Cost efficiency score (0-1, higher is better)")
    time_efficiency_score: float | None = Field(None, ge=0.0, le=1.0, description="Time efficiency score (0-1, higher is better)")
    final_evaluation_score: float | None = Field(None, ge=0.0, le=1.0, description="Final weighted evaluation score")


class EvaluationRunRequest(BaseModel):
    """Schema for running an evaluation."""

    implementation_id: int = Field(..., description="ID of the implementation to evaluate")


class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation (internal use)."""

    implementation_id: int
    task_id: int


class EvaluationRead(EvaluationBase):
    """Schema for evaluation response."""

    id: int
    implementation_id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationListItem(BaseModel):
    """Lightweight schema for listing evaluations."""

    id: int
    implementation_id: int
    implementation_version: str
    task_id: int
    status: EvaluationStatus
    started_at: datetime | None
    completed_at: datetime | None
    test_case_count: int | None
    error: str | None
    quality_score: float | None
    final_evaluation_score: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Target Task Metrics Schemas
class TargetTaskMetricsBase(BaseModel):
    """Base schema for target task metrics."""

    cost: float | None = Field(None, ge=0.0, description="Target cost (best known value)")
    time_ms: float | None = Field(None, ge=0.0, description="Target execution time in milliseconds (best known value)")
    last_updated_at: datetime | None = Field(None, description="When the targets were last updated")


class TargetTaskMetricsCreate(TargetTaskMetricsBase):
    """Schema for creating target task metrics."""
    pass


class TargetTaskMetricsUpdate(BaseModel):
    """Schema for updating target task metrics (all fields optional)."""

    cost: float | None = Field(None, ge=0.0)
    time_ms: float | None = Field(None, ge=0.0)
    last_updated_at: datetime | None = None


class TargetTaskMetricsRead(TargetTaskMetricsBase):
    """Schema for target task metrics response."""

    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Evaluation Results (per-test execution) Schemas
class EvaluationResultGradeItem(BaseModel):
    """Grade summary for an execution within an evaluation."""

    id: int
    grader_id: int
    grader_name: str | None
    score_float: float | None
    score_boolean: bool | None
    reasoning: str | None
    confidence: float | None
    grading_started_at: datetime
    grading_completed_at: datetime | None
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationResultItem(BaseModel):
    """Per-execution result for an evaluation, including test case and grades."""

    execution_result_id: int
    test_case_id: int | None
    test_case_description: str | None
    arguments: dict[str, Any] | None
    expected_output: str | None

    # Outputs
    result_text: str | None
    result_json: dict[str, Any] | None
    error: str | None

    # Execution metrics
    started_at: datetime
    completed_at: datetime | None
    prompt_tokens: int | None
    cached_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    total_tokens: int | None
    cost: float | None

    # Grades for this execution
    grades: list[EvaluationResultGradeItem]

    model_config = ConfigDict(from_attributes=True)


class ImplementationEvaluationStats(BaseModel):
    """Aggregate stats for all evaluations of an implementation."""
    
    implementation_id: int
    evaluation_count: int
    avg_quality_score: float | None = Field(None, ge=0.0, le=1.0)
    avg_cost: float | None = Field(None, ge=0.0)
    avg_execution_time_ms: float | None = Field(None, ge=0.0)
    avg_cost_efficiency_score: float | None = Field(None, ge=0.0, le=1.0)
    avg_time_efficiency_score: float | None = Field(None, ge=0.0, le=1.0)
    avg_final_evaluation_score: float | None = Field(None, ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)

