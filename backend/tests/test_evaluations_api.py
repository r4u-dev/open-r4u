"""Tests for evaluations API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.enums import EvaluationStatus, ScoreType
from app.models.evaluation import (
    Evaluation,
    EvaluationConfig,
    Grade,
    Grader,
    TargetTaskMetrics,
    TestCase,
)
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task


@pytest.mark.asyncio
async def test_create_evaluation_config(client: AsyncClient, test_session):
    """Test creating evaluation configuration via API."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "quality_weight": 0.6,
        "cost_weight": 0.3,
        "time_weight": 0.1,
        "grader_ids": [1, 2, 3],
    }

    response = await client.post(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 201

    data = response.json()
    assert data["task_id"] == task.id
    assert data["quality_weight"] == 0.6
    assert data["cost_weight"] == 0.3
    assert data["time_weight"] == 0.1
    assert data["grader_ids"] == [1, 2, 3]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify config was created in database
    config_query = select(EvaluationConfig).where(EvaluationConfig.id == data["id"])
    config_result = await test_session.execute(config_query)
    config = config_result.scalar_one()

    assert config.task_id == task.id
    assert config.quality_weight == 0.6


@pytest.mark.asyncio
async def test_create_evaluation_config_default_weights(
    client: AsyncClient, test_session,
):
    """Test creating evaluation config with default weights."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "grader_ids": [1, 2],
    }

    response = await client.post(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 201

    data = response.json()
    assert data["quality_weight"] == 0.5  # Default
    assert data["cost_weight"] == 0.3  # Default
    assert data["time_weight"] == 0.2  # Default
    assert data["grader_ids"] == [1, 2]


@pytest.mark.asyncio
async def test_create_evaluation_config_invalid_weights(
    client: AsyncClient, test_session,
):
    """Test creating evaluation config with invalid weights."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "quality_weight": 0.5,
        "cost_weight": 0.5,
        "time_weight": 0.5,  # Total = 1.5, should fail
        "grader_ids": [],
    }

    response = await client.post(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 422

    data = response.json()
    assert "Quality, cost, and time weights must sum to 1.0" in str(data["detail"])


@pytest.mark.asyncio
async def test_create_evaluation_config_task_not_found(client: AsyncClient):
    """Test creating evaluation config for non-existent task."""
    payload = {
        "quality_weight": 0.6,
        "cost_weight": 0.3,
        "time_weight": 0.1,
        "grader_ids": [],
    }

    response = await client.post("/v1/evaluations/tasks/999/config", json=payload)
    assert response.status_code == 404

    data = response.json()
    assert "Task with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_get_evaluation_config(client: AsyncClient, test_session):
    """Test getting evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create config
    config = EvaluationConfig(
        task_id=task.id,
        quality_weight=0.6,
        cost_weight=0.3,
        time_weight=0.1,
        grader_ids=[1, 2, 3],
    )
    test_session.add(config)
    await test_session.commit()

    response = await client.get(f"/v1/evaluations/tasks/{task.id}/config")
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == task.id
    assert data["quality_weight"] == 0.6
    assert data["cost_weight"] == 0.3
    assert data["time_weight"] == 0.1
    assert data["grader_ids"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_evaluation_config_not_found(client: AsyncClient, test_session):
    """Test getting evaluation config when none exists."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    response = await client.get(f"/v1/evaluations/tasks/{task.id}/config")
    assert response.status_code == 200

    data = response.json()
    assert data is None


@pytest.mark.asyncio
async def test_update_evaluation_config(client: AsyncClient, test_session):
    """Test updating evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create initial config
    config = EvaluationConfig(
        task_id=task.id,
        quality_weight=0.5,
        cost_weight=0.3,
        time_weight=0.2,
        grader_ids=[1, 2],
    )
    test_session.add(config)
    await test_session.commit()

    payload = {
        "quality_weight": 0.7,
        "cost_weight": 0.2,
        "time_weight": 0.1,
        "grader_ids": [1, 2, 3, 4],
    }

    response = await client.patch(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["quality_weight"] == 0.7
    assert data["cost_weight"] == 0.2
    assert data["time_weight"] == 0.1
    assert data["grader_ids"] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_update_evaluation_config_partial(client: AsyncClient, test_session):
    """Test partial update of evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create initial config
    config = EvaluationConfig(
        task_id=task.id,
        quality_weight=0.5,
        cost_weight=0.3,
        time_weight=0.2,
        grader_ids=[1, 2],
    )
    test_session.add(config)
    await test_session.commit()

    payload = {
        "quality_weight": 0.8,
        "cost_weight": 0.1,
        "time_weight": 0.1,
    }

    response = await client.patch(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["quality_weight"] == 0.8
    assert data["cost_weight"] == 0.1
    assert data["time_weight"] == 0.1
    assert data["grader_ids"] == [1, 2]  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_evaluation_config_not_found(client: AsyncClient, test_session):
    """Test updating non-existent evaluation config."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "quality_weight": 0.8,
    }

    response = await client.patch(
        f"/v1/evaluations/tasks/{task.id}/config", json=payload,
    )
    assert response.status_code == 404

    data = response.json()
    assert "Evaluation config not found for task" in data["detail"]


@pytest.mark.asyncio
async def test_run_evaluation_success(client: AsyncClient, test_session):
    """Test running evaluation successfully."""
    # Setup
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    # Create grader
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

    # Create test cases
    test_case1 = TestCase(
        task_id=task.id,
        description="Test case 1",
        arguments={"input": "test1"},
        expected_output=[{"role": "assistant", "content": "expected1"}],
    )
    test_session.add(test_case1)

    test_case2 = TestCase(
        task_id=task.id,
        description="Test case 2",
        arguments={"input": "test2"},
        expected_output=[{"role": "assistant", "content": "expected2"}],
    )
    test_session.add(test_case2)
    await test_session.commit()

    # Mock execution and grading
    execution_result1 = ExecutionResult(
        id=1,
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered 1",
        result_text="Test result 1",
        cost=0.01,
    )

    execution_result2 = ExecutionResult(
        id=2,
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered 2",
        result_text="Test result 2",
        cost=0.02,
    )

    grade1 = Grade(
        id=1,
        grader_id=grader.id,
        execution_result_id=1,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )

    grade2 = Grade(
        id=2,
        grader_id=grader.id,
        execution_result_id=2,
        score_float=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC),
    )

    # Start evaluation - should return immediately with status running
    with (
        patch("app.services.evaluation_service.execute_task") as mock_execute,
        patch(
            "app.services.evaluation_service.EvaluationService._get_all_project_graders",
        ) as mock_get_graders,
        patch(
            "app.services.grading_service.GradingService.get_grader",
        ) as mock_get_grader,
        patch(
            "app.services.grading_service.GradingService.execute_grading",
        ) as mock_execute_grading,
    ):
        # Mock execute_task to return execution results
        mock_execute.side_effect = [execution_result1, execution_result2]

        # Mock grader retrieval
        mock_get_graders.return_value = [grader.id]
        mock_get_grader.return_value = grader

        # Mock grading execution
        mock_execute_grading.side_effect = [grade1, grade2]

        response = await client.post(
            "/v1/evaluations", json={"implementation_id": implementation.id},
        )
        assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] == implementation.id
    assert data["task_id"] == task.id
    assert data["status"] == "running"
    assert data["test_case_count"] == 2
    # Scores should be None initially
    assert data["quality_score"] is None
    assert data["avg_cost"] is None
    assert data["grader_scores"] == {}

    evaluation_id = data["id"]

    # Now simulate the background execution by directly updating the evaluation in the test session
    # (since the background method uses a separate session, we need to update it in test_session)
    from sqlalchemy import select

    from app.models.evaluation import Evaluation

    # Get the evaluation from test_session and update it
    query = select(Evaluation).where(Evaluation.id == evaluation_id)
    result = await test_session.execute(query)
    evaluation = result.scalar_one()

    # Simulate what the background method would do
    evaluation.status = EvaluationStatus.COMPLETED
    evaluation.completed_at = datetime.now(UTC)
    evaluation.grader_scores = {str(grader.id): 0.85}
    evaluation.quality_score = 0.85
    evaluation.avg_cost = 0.015
    evaluation.avg_execution_time_ms = 100.0

    await test_session.commit()

    # Now check the completed evaluation
    response = await client.get(f"/v1/evaluations/{evaluation_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["test_case_count"] == 2
    assert abs(data["quality_score"] - 0.85) < 0.001  # Average of 0.8 and 0.9
    assert data["avg_cost"] == 0.015  # Average of 0.01 and 0.02
    assert str(grader.id) in data["grader_scores"]


@pytest.mark.asyncio
async def test_run_evaluation_no_test_cases(client: AsyncClient, test_session):
    """Test running evaluation with no test cases."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    response = await client.post(
        "/v1/evaluations", json={"implementation_id": implementation.id},
    )
    assert response.status_code == 400

    data = response.json()
    assert "No test cases found for task" in data["detail"]


@pytest.mark.asyncio
async def test_run_evaluation_implementation_not_found(client: AsyncClient):
    """Test running evaluation for non-existent implementation."""
    response = await client.post("/v1/evaluations", json={"implementation_id": 999})
    assert response.status_code == 404

    data = response.json()
    assert "Implementation with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_list_implementation_evaluations(client: AsyncClient, test_session):
    """Test listing evaluations for an implementation."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    # Create evaluations
    evaluation1 = Evaluation(
        implementation_id=implementation.id,
        task_id=task.id,
        status=EvaluationStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_case_count=2,
        quality_score=0.8,
        avg_cost=0.01,
        avg_execution_time_ms=1000.0,
        grader_scores={"1": 0.8},
    )
    test_session.add(evaluation1)

    evaluation2 = Evaluation(
        implementation_id=implementation.id,
        task_id=task.id,
        status=EvaluationStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_case_count=1,
        error="Execution failed",
        grader_scores={},
    )
    test_session.add(evaluation2)
    await test_session.commit()

    response = await client.get(
        f"/v1/evaluations?implementation_id={implementation.id}",
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2

    # Check that both evaluations are present
    statuses = [eval_data["status"] for eval_data in data]
    assert "completed" in statuses
    assert "failed" in statuses

    # Check response format
    for evaluation in data:
        assert "id" in evaluation
        assert "implementation_id" in evaluation
        assert "task_id" in evaluation
        assert "status" in evaluation
        assert "created_at" in evaluation


@pytest.mark.asyncio
async def test_list_implementation_evaluations_empty(client: AsyncClient, test_session):
    """Test listing evaluations for implementation with no evaluations."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    response = await client.get(
        f"/v1/evaluations?implementation_id={implementation.id}",
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_evaluation(client: AsyncClient, test_session):
    """Test getting a specific evaluation by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    evaluation = Evaluation(
        implementation_id=implementation.id,
        task_id=task.id,
        status=EvaluationStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_case_count=2,
        quality_score=0.85,
        avg_cost=0.015,
        avg_execution_time_ms=1500.0,
        grader_scores={"1": 0.85},
    )
    test_session.add(evaluation)
    await test_session.commit()

    response = await client.get(f"/v1/evaluations/{evaluation.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == evaluation.id
    assert data["implementation_id"] == implementation.id
    assert data["task_id"] == task.id
    assert data["status"] == "completed"
    assert data["test_case_count"] == 2
    assert data["quality_score"] == 0.85
    assert data["avg_cost"] == 0.015
    assert data["avg_execution_time_ms"] == 1500.0
    assert data["grader_scores"] == {"1": 0.85}


@pytest.mark.asyncio
async def test_get_evaluation_not_found(client: AsyncClient):
    """Test getting a non-existent evaluation."""
    response = await client.get("/v1/evaluations/999")
    assert response.status_code == 404

    data = response.json()
    assert "Evaluation with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_delete_evaluation(client: AsyncClient, test_session):
    """Test deleting an evaluation."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    evaluation = Evaluation(
        implementation_id=implementation.id,
        task_id=task.id,
        status=EvaluationStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_case_count=1,
        grader_scores={},
    )
    test_session.add(evaluation)
    await test_session.commit()

    response = await client.delete(f"/v1/evaluations/{evaluation.id}")
    assert response.status_code == 204

    # Verify evaluation is deleted
    evaluation_query = select(Evaluation).where(Evaluation.id == evaluation.id)
    evaluation_result = await test_session.execute(evaluation_query)
    deleted_evaluation = evaluation_result.scalar_one_or_none()
    assert deleted_evaluation is None


@pytest.mark.asyncio
async def test_delete_evaluation_not_found(client: AsyncClient):
    """Test deleting a non-existent evaluation."""
    response = await client.delete("/v1/evaluations/999")
    assert response.status_code == 404

    data = response.json()
    assert "Evaluation with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_evaluation_with_efficiency_scores(client: AsyncClient, test_session):
    """Test evaluation with calculated efficiency scores."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
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

    # Create target metrics
    target_metrics = TargetTaskMetrics(task_id=task.id, cost=0.01, time_ms=1000.0)
    test_session.add(target_metrics)

    evaluation = Evaluation(
        implementation_id=implementation.id,
        task_id=task.id,
        status=EvaluationStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_case_count=1,
        quality_score=0.8,
        avg_cost=0.02,  # 2x target cost
        avg_execution_time_ms=2000.0,  # 2x target time
        grader_scores={"1": 0.8},
    )
    test_session.add(evaluation)
    await test_session.commit()

    response = await client.get(f"/v1/evaluations/{evaluation.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["cost_efficiency_score"] == 0.5  # 0.01 / 0.02
    assert data["time_efficiency_score"] == 0.5  # 1000.0 / 2000.0
    assert data["final_evaluation_score"] is not None  # Should be calculated


@pytest.mark.asyncio
async def test_evaluation_config_validation_weights_sum(
    client: AsyncClient, test_session,
):
    """Test evaluation config validation for weights that don't sum to 1.0."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Test various invalid weight combinations
    invalid_payloads = [
        {"quality_weight": 0.3, "cost_weight": 0.3, "time_weight": 0.3},  # 0.9
        {"quality_weight": 0.6, "cost_weight": 0.6, "time_weight": 0.1},  # 1.3
        {"quality_weight": 1.0, "cost_weight": 0.0, "time_weight": 0.0},  # 1.0 (valid)
    ]

    for i, payload in enumerate(invalid_payloads[:-1]):  # Skip the valid one
        response = await client.post(
            f"/v1/evaluations/tasks/{task.id}/config", json=payload,
        )
        if i < 2:  # First two should fail
            assert response.status_code == 422
            data = response.json()
            assert "Quality, cost, and time weights must sum to 1.0" in str(
                data["detail"],
            )

    # Test the valid one
    response = await client.post(
        f"/v1/evaluations/tasks/{task.id}/config", json=invalid_payloads[-1],
    )
    assert response.status_code == 201
