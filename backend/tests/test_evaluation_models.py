"""Tests for evaluation models (Grader and Grade)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.enums import ScoreType
from app.models.evaluation import Grade, Grader
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace


@pytest.mark.asyncio
async def test_create_grader(test_session):
    """Test creating a grader."""
    # Create project first
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        description="Evaluates response accuracy",
        prompt="Rate the accuracy of this response: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        temperature=0.0,
        max_output_tokens=500,
        is_active=True)

    test_session.add(grader)
    await test_session.commit()
    await test_session.refresh(grader)

    assert grader.id is not None
    assert grader.project_id == project.id
    assert grader.name == "accuracy"
    assert grader.description == "Evaluates response accuracy"
    assert grader.prompt == "Rate the accuracy of this response: {{context}}"
    assert grader.score_type == ScoreType.FLOAT
    assert grader.model == "gpt-4"
    assert grader.temperature == 0.0
    assert grader.max_output_tokens == 500
    assert grader.is_active is True
    assert grader.created_at is not None
    assert grader.updated_at is not None


@pytest.mark.asyncio
async def test_create_grader_with_reasoning_and_schema(test_session):
    """Test creating a grader with reasoning and response schema."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="toxicity",
        description="Evaluates content toxicity",
        prompt="Check if this content is toxic: {{context}}",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        temperature=0.0,
        reasoning={"effort": "medium"},
        response_schema={
            "type": "object",
            "properties": {
                "score": {"type": "boolean"},
                "reasoning": {"type": "string"},
                "confidence": {"type": "number"},
            },
        },
        max_output_tokens=300,
        is_active=True)

    test_session.add(grader)
    await test_session.commit()
    await test_session.refresh(grader)

    assert grader.score_type == ScoreType.BOOLEAN
    assert grader.reasoning == {"effort": "medium"}
    assert grader.response_schema["type"] == "object"
    assert grader.response_schema["properties"]["score"]["type"] == "boolean"


@pytest.mark.asyncio
async def test_grader_project_relationship(test_session):
    """Test grader-project relationship."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)

    test_session.add(grader)
    await test_session.commit()
    await test_session.refresh(grader)

    # Test relationship
    assert grader.project.id == project.id
    assert grader.project.name == "Test Project"

    # Test back reference
    project_graders = await test_session.execute(
        select(Grader).where(Grader.project_id == project.id))
    graders = project_graders.scalars().all()
    assert len(graders) == 1
    assert graders[0].name == "accuracy"


@pytest.mark.asyncio
async def test_create_grade_for_trace(test_session):
    """Test creating a grade for a trace."""
    # Create project and grader
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    # Create trace
    trace = Trace(
        project_id=project.id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    # Create grade
    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.85,
        reasoning="The response is mostly accurate",
        confidence=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150)

    test_session.add(grade)
    await test_session.commit()
    await test_session.refresh(grade)

    assert grade.id is not None
    assert grade.grader_id == grader.id
    assert grade.trace_id == trace.id
    assert grade.execution_result_id is None
    assert grade.score_float == 0.85
    assert grade.score_boolean is None
    assert grade.reasoning == "The response is mostly accurate"
    assert grade.confidence == 0.9
    assert grade.prompt_tokens == 100
    assert grade.completion_tokens == 50
    assert grade.total_tokens == 150


@pytest.mark.asyncio
async def test_create_grade_for_execution_result(test_session):
    """Test creating a grade for an execution result."""
    # Create project, task, and implementation
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        version="0.1",
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    # Create grader
    grader = Grader(
        project_id=project.id,
        name="toxicity",
        prompt="Test prompt",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    # Create execution result
    execution_result = ExecutionResult(
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered",
        result_text="Test execution result")
    test_session.add(execution_result)
    await test_session.flush()

    # Create grade
    grade = Grade(
        grader_id=grader.id,
        execution_result_id=execution_result.id,
        score_boolean=False,
        reasoning="Content is not toxic",
        confidence=0.95,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))

    test_session.add(grade)
    await test_session.commit()
    await test_session.refresh(grade)

    assert grade.id is not None
    assert grade.grader_id == grader.id
    assert grade.trace_id is None
    assert grade.execution_result_id == execution_result.id
    assert grade.score_float is None
    assert grade.score_boolean is False
    assert grade.reasoning == "Content is not toxic"
    assert grade.confidence == 0.95


@pytest.mark.asyncio
async def test_grade_relationships(test_session):
    """Test grade relationships with grader, trace, and execution result."""
    # Create project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create grader
    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    # Create trace
    trace = Trace(
        project_id=project.id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    # Create grade
    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.75,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))
    test_session.add(grade)
    await test_session.commit()
    await test_session.refresh(grade)

    # Test relationships
    assert grade.grader.id == grader.id
    assert grade.grader.name == "accuracy"
    assert grade.trace.id == trace.id
    # Removed assertion on trace.result (now using output_items)
    assert grade.execution_result is None


@pytest.mark.asyncio
async def test_grade_with_error(test_session):
    """Test creating a grade with an error."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
        error="LLM API timeout")

    test_session.add(grade)
    await test_session.commit()
    await test_session.refresh(grade)

    assert grade.error == "LLM API timeout"
    assert grade.score_float is None
    assert grade.score_boolean is None
    assert grade.reasoning is None


@pytest.mark.asyncio
async def test_grade_with_grader_response(test_session):
    """Test creating a grade with raw grader response."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    grader_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [
            {"message": {"content": '{"score": 0.8, "reasoning": "Good response"}'}},
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
    }

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        reasoning="Good response",
        grader_response=grader_response,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70)

    test_session.add(grade)
    await test_session.commit()
    await test_session.refresh(grade)

    assert grade.grader_response["id"] == "chatcmpl-123"
    assert grade.grader_response["model"] == "gpt-4"
    assert grade.prompt_tokens == 50
    assert grade.completion_tokens == 20
    assert grade.total_tokens == 70


@pytest.mark.asyncio
async def test_grader_cascade_delete(test_session):
    """Test that deleting a grader cascades to grades."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))
    test_session.add(grade)
    await test_session.commit()

    # Delete grader
    await test_session.delete(grader)
    await test_session.commit()

    # Check that grade was also deleted
    grade_query = select(Grade).where(Grade.id == grade.id)
    grade_result = await test_session.execute(grade_query)
    deleted_grade = grade_result.scalar_one_or_none()
    assert deleted_grade is None


@pytest.mark.asyncio
async def test_grade_polymorphic_constraint(test_session):
    """Test that grade requires exactly one target (trace or execution result)."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.commit()  # Commit the project so it persists across rollbacks

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.commit()  # Commit the grader so it persists across rollbacks

    # Store the IDs as they might be expired after rollback
    grader_id = grader.id
    project_id = project.id

    # Test grade with both trace_id and execution_result_id (should fail)
    grade_both = Grade(
        grader_id=grader_id,
        trace_id=1,
        execution_result_id=1,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))
    test_session.add(grade_both)

    with pytest.raises(Exception):  # Should raise constraint violation
        await test_session.commit()

    await test_session.rollback()

    # Test grade with neither trace_id nor execution_result_id (should fail)
    grade_neither = Grade(
        grader_id=grader_id,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))
    test_session.add(grade_neither)

    with pytest.raises(Exception):  # Should raise constraint violation
        await test_session.commit()

    await test_session.rollback()

    # Test grade with only trace_id (should succeed)
    trace = Trace(
        project_id=project_id,
        model="gpt-4", started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC))
    test_session.add(trace)
    await test_session.flush()

    grade_valid = Grade(
        grader_id=grader_id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))
    test_session.add(grade_valid)

    await test_session.commit()  # Should succeed
    assert grade_valid.id is not None
