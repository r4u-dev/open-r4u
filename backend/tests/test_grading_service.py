"""Tests for grading service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from app.config import Settings
from app.enums import ScoreType
from app.models.evaluation import Grade, Grader
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.services.grading_service import GradingService, NotFoundError, BadRequestError
from app.schemas.executions import ExecutionResultBase


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="test-key",
    )


@pytest.fixture
def grading_service(settings):
    """Create grading service instance."""
    return GradingService(settings)


@pytest.mark.asyncio
async def test_create_grader(grading_service, test_session):
    """Test creating a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        description="Evaluates accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
        temperature=0.0,
        is_active=True,
    )

    assert grader.id is not None
    assert grader.project_id == project.id
    assert grader.name == "accuracy"
    assert grader.description == "Evaluates accuracy"
    assert grader.prompt == "Rate accuracy: {{context}}"
    assert grader.score_type == ScoreType.FLOAT
    assert grader.model == "gpt-4"
    assert grader.max_output_tokens == 500
    assert grader.temperature == 0.0
    assert grader.is_active is True


@pytest.mark.asyncio
async def test_get_grader(grading_service, test_session):
    """Test getting a grader by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    retrieved_grader = await grading_service.get_grader(test_session, grader.id)
    assert retrieved_grader.id == grader.id
    assert retrieved_grader.name == "accuracy"


@pytest.mark.asyncio
async def test_get_grader_not_found(grading_service, test_session):
    """Test getting a non-existent grader."""
    with pytest.raises(NotFoundError, match="Grader with id 999 not found"):
        await grading_service.get_grader(test_session, 999)


@pytest.mark.asyncio
async def test_list_graders(grading_service, test_session):
    """Test listing graders for a project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create graders
    grader1 = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt 1",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    grader2 = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="toxicity",
        prompt="Test prompt 2",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )

    graders_with_counts = await grading_service.list_graders(test_session, project.id)
    assert len(graders_with_counts) == 2
    
    grader_names = [grader.name for grader, _ in graders_with_counts]
    assert "accuracy" in grader_names
    assert "toxicity" in grader_names
    
    # Check grade counts (should be 0 for new graders)
    for grader, count in graders_with_counts:
        assert count == 0


@pytest.mark.asyncio
async def test_update_grader(grading_service, test_session):
    """Test updating a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    updated_grader = await grading_service.update_grader(
        session=test_session,
        grader_id=grader.id,
        name="accuracy_v2",
        temperature=0.5,
        is_active=False,
    )

    assert updated_grader.name == "accuracy_v2"
    assert updated_grader.temperature == 0.5
    assert updated_grader.is_active is False
    assert updated_grader.prompt == "Test prompt"  # Should remain unchanged


@pytest.mark.asyncio
async def test_delete_grader(grading_service, test_session):
    """Test deleting a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    await grading_service.delete_grader(test_session, grader.id)

    # Verify grader is deleted
    with pytest.raises(NotFoundError):
        await grading_service.get_grader(test_session, grader.id)


@pytest.mark.asyncio
async def test_parse_grading_response_json_float(grading_service):
    """Test parsing JSON response with float score."""
    result_json = {
        "score": 0.85,
        "reasoning": "The response is mostly accurate",
        "confidence": 0.9
    }

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=None,
        result_json=result_json,
        score_type=ScoreType.FLOAT,
    )

    assert score_float == 0.85
    assert score_boolean is None
    assert reasoning == "The response is mostly accurate"
    assert confidence == 0.9


@pytest.mark.asyncio
async def test_parse_grading_response_json_boolean(grading_service):
    """Test parsing JSON response with boolean score."""
    result_json = {
        "score": False,
        "reasoning": "Content is not toxic",
        "confidence": 0.95
    }

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=None,
        result_json=result_json,
        score_type=ScoreType.BOOLEAN,
    )

    assert score_float is None
    assert score_boolean is False
    assert reasoning == "Content is not toxic"
    assert confidence == 0.95


@pytest.mark.asyncio
async def test_parse_grading_response_text_json(grading_service):
    """Test parsing text response that contains JSON."""
    result_text = '{"score": 0.75, "reasoning": "Good response", "confidence": 0.8}'

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=result_text,
        result_json=None,
        score_type=ScoreType.FLOAT,
    )

    assert score_float == 0.75
    assert score_boolean is None
    assert reasoning == "Good response"
    assert confidence == 0.8


@pytest.mark.asyncio
async def test_parse_grading_response_text_boolean(grading_service):
    """Test parsing text response for boolean score."""
    result_text = "The content is not toxic. Score: true"

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=result_text,
        result_json=None,
        score_type=ScoreType.BOOLEAN,
    )

    assert score_float is None
    assert score_boolean is True
    assert reasoning == result_text


@pytest.mark.asyncio
async def test_parse_grading_response_text_boolean_false(grading_service):
    """Test parsing text response for boolean false score."""
    result_text = "The content is toxic. Score: false"

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=result_text,
        result_json=None,
        score_type=ScoreType.BOOLEAN,
    )

    assert score_float is None
    assert score_boolean is False
    assert reasoning == result_text


@pytest.mark.asyncio
async def test_parse_grading_response_text_pass_fail(grading_service):
    """Test parsing text response with pass/fail keywords."""
    result_text = "The response passes the accuracy test"

    score_float, score_boolean, reasoning, confidence = grading_service._parse_grading_response(
        result_text=result_text,
        result_json=None,
        score_type=ScoreType.BOOLEAN,
    )

    assert score_float is None
    assert score_boolean is True
    assert reasoning == result_text


@pytest.mark.asyncio
async def test_execute_grading_trace_success(grading_service, test_session):
    """Test executing grading for a trace successfully."""
    # Setup
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    # Mock the executor
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Rate accuracy: Test response",
        result_text='{"score": 0.8, "reasoning": "Good response", "confidence": 0.9}',
        result_json={"score": 0.8, "reasoning": "Good response", "confidence": 0.9},
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
        system_fingerprint="fp-test",
    )

    with patch('app.services.grading_service.LLMExecutor') as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        grade = await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            trace_id=trace.id,
        )

    assert grade.id is not None
    assert grade.grader_id == grader.id
    assert grade.trace_id == trace.id
    assert grade.execution_result_id is None
    assert grade.score_float == 0.8
    assert grade.score_boolean is None
    assert grade.reasoning == "Good response"
    assert grade.confidence == 0.9
    assert grade.prompt_tokens == 50
    assert grade.completion_tokens == 30
    assert grade.total_tokens == 80
    assert grade.system_fingerprint == "fp-test"
    assert grade.error is None


@pytest.mark.asyncio
async def test_execute_grading_execution_result_success(grading_service, test_session):
    """Test executing grading for an execution result successfully."""
    # Setup
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
        max_output_tokens=500,
    )
    test_session.add(implementation)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="toxicity",
        prompt="Check toxicity: {{context}}",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )

    execution_result = ExecutionResult(
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Test prompt rendered",
        result_text="Test execution result",
    )
    test_session.add(execution_result)
    await test_session.flush()

    # Mock the executor
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Check toxicity: Test execution result",
        result_text='{"score": false, "reasoning": "Not toxic", "confidence": 0.95}',
        result_json={"score": False, "reasoning": "Not toxic", "confidence": 0.95},
        prompt_tokens=40,
        completion_tokens=20,
        total_tokens=60,
    )

    with patch('app.services.grading_service.LLMExecutor') as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        grade = await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            execution_result_id=execution_result.id,
        )

    assert grade.id is not None
    assert grade.grader_id == grader.id
    assert grade.trace_id is None
    assert grade.execution_result_id == execution_result.id
    assert grade.score_float is None
    assert grade.score_boolean is False
    assert grade.reasoning == "Not toxic"
    assert grade.confidence == 0.95


@pytest.mark.asyncio
async def test_execute_grading_inactive_grader(grading_service, test_session):
    """Test executing grading with an inactive grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
        is_active=False,  # Inactive grader
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    with pytest.raises(BadRequestError, match="Grader .* is not active"):
        await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            trace_id=trace.id,
        )


@pytest.mark.asyncio
async def test_execute_grading_no_target(grading_service, test_session):
    """Test executing grading with no target specified."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    with pytest.raises(BadRequestError, match="Specify exactly one of trace_id or execution_result_id"):
        await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
        )


@pytest.mark.asyncio
async def test_execute_grading_both_targets(grading_service, test_session):
    """Test executing grading with both targets specified."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    with pytest.raises(BadRequestError, match="Specify exactly one of trace_id or execution_result_id"):
        await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            trace_id=1,
            execution_result_id=1,
        )


@pytest.mark.asyncio
async def test_execute_grading_trace_not_found(grading_service, test_session):
    """Test executing grading with non-existent trace."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    with pytest.raises(NotFoundError, match="Trace with id 999 not found"):
        await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            trace_id=999,
        )


@pytest.mark.asyncio
async def test_execute_grading_executor_error(grading_service, test_session):
    """Test executing grading when executor returns an error."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    # Mock the executor to return an error
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Test prompt",
        error="API timeout",
    )

    with patch('app.services.grading_service.LLMExecutor') as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        grade = await grading_service.execute_grading(
            session=test_session,
            grader_id=grader.id,
            trace_id=trace.id,
        )

    assert grade.id is not None
    assert grade.grader_id == grader.id
    assert grade.trace_id == trace.id
    assert grade.error == "API timeout"
    assert grade.score_float is None
    assert grade.score_boolean is None
    assert grade.reasoning is None


@pytest.mark.asyncio
async def test_list_grades_for_trace(grading_service, test_session):
    """Test listing grades for a trace."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    # Create grades
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(timezone.utc),
        grading_completed_at=datetime.now(timezone.utc),
    )
    test_session.add(grade1)
    await test_session.flush()  # Flush to get the first grade committed

    # Add a small delay to ensure different timestamps
    import time
    time.sleep(0.001)

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.9,
        grading_started_at=datetime.now(timezone.utc),
        grading_completed_at=datetime.now(timezone.utc),
    )
    test_session.add(grade2)
    await test_session.commit()

    grades = await grading_service.list_grades(test_session, trace_id=trace.id)
    assert len(grades) == 2
    
    # Check that both grades are present (order may vary due to timing)
    scores = [grade.score_float for grade in grades]
    assert 0.8 in scores
    assert 0.9 in scores


@pytest.mark.asyncio
async def test_list_grades_for_execution(grading_service, test_session):
    """Test listing grades for an execution result."""
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
        max_output_tokens=500,
    )
    test_session.add(implementation)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="toxicity",
        prompt="Test prompt",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )

    execution_result = ExecutionResult(
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        prompt_rendered="Test prompt rendered",
        result_text="Test execution result",
    )
    test_session.add(execution_result)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        execution_result_id=execution_result.id,
        score_boolean=False,
        grading_started_at=datetime.now(timezone.utc),
        grading_completed_at=datetime.now(timezone.utc),
    )
    test_session.add(grade)
    await test_session.commit()

    grades = await grading_service.list_grades(test_session, execution_result_id=execution_result.id)
    assert len(grades) == 1
    assert grades[0].score_boolean is False


@pytest.mark.asyncio
async def test_list_grades_for_grader(grading_service, test_session):
    """Test listing grades for a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.85,
        grading_started_at=datetime.now(timezone.utc),
        grading_completed_at=datetime.now(timezone.utc),
    )
    test_session.add(grade)
    await test_session.commit()

    grades = await grading_service.list_grades(test_session, grader_id=grader.id)
    assert len(grades) == 1
    assert grades[0].score_float == 0.85


@pytest.mark.asyncio
async def test_delete_grade(grading_service, test_session):
    """Test deleting a grade."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = await grading_service.create_grader(
        session=test_session,
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(timezone.utc),
        grading_completed_at=datetime.now(timezone.utc),
    )
    test_session.add(grade)
    await test_session.commit()

    await grading_service.delete_grade(test_session, grade.id)

    # Verify grade is deleted
    with pytest.raises(NotFoundError):
        await grading_service.get_grade(test_session, grade.id)
