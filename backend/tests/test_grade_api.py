"""Tests for grade API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.enums import ScoreType
from app.models.evaluation import Grade, Grader
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.executions import ExecutionResultBase


@pytest.mark.asyncio
async def test_create_grade_for_trace(client: AsyncClient, test_session):
    """Test creating a grade for a trace."""
    # Setup
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    # Mock the executor
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Rate accuracy: Test response",
        result_text='{"score": 0.8, "reasoning": "Good response", "confidence": 0.9}',
        result_json=None,  # result_json is now list[OutputItem], parsing handled from result_text
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
    )

    with patch("app.services.grading_service.LLMExecutor") as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        payload = {"trace_id": trace.id}
        response = await client.post(
            "/v1/grades",
            json={**payload, "grader_id": grader.id},
        )
        assert response.status_code == 201

    data = response.json()
    assert data["grader_id"] == grader.id
    assert data["trace_id"] == trace.id
    assert data["execution_result_id"] is None
    assert data["score_float"] == 0.8
    assert data["score_boolean"] is None
    assert data["reasoning"] == "Good response"
    assert data["confidence"] == 0.9
    assert data["prompt_tokens"] == 50
    assert data["completion_tokens"] == 30
    assert data["total_tokens"] == 80
    assert data["error"] is None
    assert "id" in data
    assert "grading_started_at" in data
    assert "grading_completed_at" in data


@pytest.mark.asyncio
async def test_create_grade_for_execution_result(client: AsyncClient, test_session):
    """Test creating a grade for an execution result."""
    # Setup
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
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

    grader = Grader(
        project_id=project.id,
        name="toxicity",
        prompt="Check toxicity: {{context}}",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )
    test_session.add(grader)
    await test_session.flush()

    execution_result = ExecutionResult(
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered",
        result_text="Test execution result",
    )
    test_session.add(execution_result)
    await test_session.flush()

    # Mock the executor
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Check toxicity: Test execution result",
        result_text='{"score": false, "reasoning": "Not toxic", "confidence": 0.95}',
        result_json=None,  # result_json is now list[OutputItem], parsing handled from result_text
        prompt_tokens=40,
        completion_tokens=20,
        total_tokens=60,
    )

    with patch("app.services.grading_service.LLMExecutor") as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        payload = {"execution_result_id": execution_result.id}
        response = await client.post(
            "/v1/grades",
            json={**payload, "grader_id": grader.id},
        )
        assert response.status_code == 201

    data = response.json()
    assert data["grader_id"] == grader.id
    assert data["trace_id"] is None
    assert data["execution_result_id"] == execution_result.id
    assert data["score_float"] is None
    assert data["score_boolean"] is False
    assert data["reasoning"] == "Not toxic"
    assert data["confidence"] == 0.95


@pytest.mark.asyncio
async def test_create_grade_no_target(client: AsyncClient, test_session):
    """Test creating a grade with no target specified."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {}  # No trace_id or execution_result_id

    response = await client.post("/v1/grades", json={**payload, "grader_id": grader.id})
    assert response.status_code == 400

    data = response.json()
    assert "Specify exactly one of trace_id or execution_result_id" in data["detail"]


@pytest.mark.asyncio
async def test_create_grade_both_targets(client: AsyncClient, test_session):
    """Test creating a grade with both targets specified."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {
        "trace_id": 1,
        "execution_result_id": 1,
    }

    response = await client.post("/v1/grades", json={**payload, "grader_id": grader.id})
    assert response.status_code == 422

    data = response.json()
    assert "Specify exactly one of trace_id or execution_result_id" in str(data)


@pytest.mark.asyncio
async def test_create_grade_grader_not_found(client: AsyncClient):
    """Test creating a grade with non-existent grader."""
    payload = {"grader_id": 999, "trace_id": 1}

    response = await client.post("/v1/grades", json=payload)
    assert response.status_code == 404

    data = response.json()
    assert "Grader with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_create_grade_trace_not_found(client: AsyncClient, test_session):
    """Test creating a grade with non-existent trace."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {"trace_id": 999}

    response = await client.post("/v1/grades", json={**payload, "grader_id": grader.id})
    assert response.status_code == 404

    data = response.json()
    assert "Trace with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_create_grade_execution_result_not_found(
    client: AsyncClient,
    test_session,
):
    """Test creating a grade with non-existent execution result."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {"execution_result_id": 999}

    response = await client.post("/v1/grades", json={**payload, "grader_id": grader.id})
    assert response.status_code == 404

    data = response.json()
    assert "ExecutionResult with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_create_grade_inactive_grader(client: AsyncClient, test_session):
    """Test creating a grade with inactive grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
        is_active=False,  # Inactive grader
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    payload = {"trace_id": trace.id}

    response = await client.post("/v1/grades", json={**payload, "grader_id": grader.id})
    assert response.status_code == 400

    data = response.json()
    assert "is not active" in data["detail"]


@pytest.mark.asyncio
async def test_create_grade_executor_error(client: AsyncClient, test_session):
    """Test creating a grade when executor returns an error."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    # Mock the executor to return an error
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt",
        error="API timeout",
    )

    with patch("app.services.grading_service.LLMExecutor") as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        payload = {"trace_id": trace.id}
        response = await client.post(
            "/v1/grades",
            json={**payload, "grader_id": grader.id},
        )
        assert response.status_code == 201  # Grade is still created with error

    data = response.json()
    assert data["error"] == "API timeout"
    assert data["score_float"] is None
    assert data["score_boolean"] is None
    assert data["reasoning"] is None


@pytest.mark.asyncio
async def test_get_grade(client: AsyncClient, test_session):
    """Test getting a specific grade by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.85,
        reasoning="Good response",
        confidence=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
    )
    test_session.add(grade)
    await test_session.commit()

    response = await client.get(f"/v1/grades/{grade.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == grade.id
    assert data["grader_id"] == grader.id
    assert data["trace_id"] == trace.id
    assert data["execution_result_id"] is None
    assert data["score_float"] == 0.85
    assert data["score_boolean"] is None
    assert data["reasoning"] == "Good response"
    assert data["confidence"] == 0.9
    assert data["prompt_tokens"] == 50
    assert data["completion_tokens"] == 30
    assert data["total_tokens"] == 80


@pytest.mark.asyncio
async def test_get_grade_not_found(client: AsyncClient):
    """Test getting a non-existent grade."""
    response = await client.get("/v1/grades/999")
    assert response.status_code == 404

    data = response.json()
    assert "Grade with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_list_grades_for_trace(client: AsyncClient, test_session):
    """Test listing grades for a trace."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    # Create grades
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )
    test_session.add(grade1)

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )
    test_session.add(grade2)
    await test_session.commit()

    response = await client.get(f"/v1/grades?trace_id={trace.id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2

    # Check that both grades are present (order may vary due to timing)
    scores = [grade["score_float"] for grade in data]
    assert 0.8 in scores
    assert 0.9 in scores


@pytest.mark.asyncio
async def test_list_grades_for_execution_result(client: AsyncClient, test_session):
    """Test listing grades for an execution result."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
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

    grader = Grader(
        project_id=project.id,
        name="toxicity",
        prompt="Test prompt",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )
    test_session.add(grader)
    await test_session.flush()

    execution_result = ExecutionResult(
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered",
        result_text="Test execution result",
    )
    test_session.add(execution_result)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        execution_result_id=execution_result.id,
        score_boolean=False,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )
    test_session.add(grade)
    await test_session.commit()

    response = await client.get(f"/v1/grades?execution_result_id={execution_result.id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["score_boolean"] is False
    assert data[0]["execution_result_id"] == execution_result.id


@pytest.mark.asyncio
async def test_list_grades_for_grader(client: AsyncClient, test_session):
    """Test listing grades for a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.85,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )
    test_session.add(grade)
    await test_session.commit()

    response = await client.get(f"/v1/grades?grader_id={grader.id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["score_float"] == 0.85
    assert data[0]["grader_id"] == grader.id


@pytest.mark.asyncio
async def test_list_grades_empty(client: AsyncClient, test_session):
    """Test listing grades when none exist."""
    response = await client.get("/v1/grades?trace_id=999")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_delete_grade(client: AsyncClient, test_session):
    """Test deleting a grade."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    grade = Grade(
        grader_id=grader.id,
        trace_id=trace.id,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )
    test_session.add(grade)
    await test_session.commit()

    response = await client.delete(f"/v1/grades/{grade.id}")
    assert response.status_code == 204

    # Verify grade is deleted
    grade_query = select(Grade).where(Grade.id == grade.id)
    grade_result = await test_session.execute(grade_query)
    deleted_grade = grade_result.scalar_one_or_none()
    assert deleted_grade is None


@pytest.mark.asyncio
async def test_delete_grade_not_found(client: AsyncClient):
    """Test deleting a non-existent grade."""
    response = await client.delete("/v1/grades/999")
    assert response.status_code == 404

    data = response.json()
    assert "Grade with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_grade_with_grader_response(client: AsyncClient, test_session):
    """Test creating a grade with grader response metadata."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
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

    # Mock the executor
    mock_execution_result = ExecutionResultBase(
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt",
        result_text='{"score": 0.8, "reasoning": "Good response"}',
        result_json=None,  # result_json is now list[OutputItem], parsing handled from result_text
        provider_response=grader_response,
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70,
    )

    with patch("app.services.grading_service.LLMExecutor") as mock_executor_class:
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = mock_execution_result
        mock_executor_class.return_value = mock_executor

        payload = {"trace_id": trace.id}
        response = await client.post(
            "/v1/grades",
            json={**payload, "grader_id": grader.id},
        )
        assert response.status_code == 201

    data = response.json()
    assert data["grader_response"]["id"] == "chatcmpl-123"
    assert data["grader_response"]["model"] == "gpt-4"
    assert data["prompt_tokens"] == 50
    assert data["completion_tokens"] == 20
    assert data["total_tokens"] == 70
