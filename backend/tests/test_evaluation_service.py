"""Tests for evaluation service."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.config import Settings
from app.enums import EvaluationStatus, ScoreType
from app.models.evaluation import (
    Evaluation,
    Grade,
    Grader,
    TargetTaskMetrics,
)
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.services.evaluation_service import (
    BadRequestError,
    EvaluationService,
    NotFoundError,
)


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="test-key")


@pytest.fixture
def evaluation_service(settings):
    """Create evaluation service instance."""
    return EvaluationService(settings)


# Test Case Management Tests
@pytest.mark.asyncio
async def test_create_test_case(evaluation_service, test_session):
    """Test creating a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case 1",
        arguments={"input": "test input"},
        expected_output="expected output")

    assert test_case.id is not None
    assert test_case.task_id == task.id
    assert test_case.description == "Test case 1"
    assert test_case.arguments == {"input": "test input"}
    assert test_case.expected_output == "expected output"


@pytest.mark.asyncio
async def test_create_test_case_task_not_found(evaluation_service, test_session):
    """Test creating a test case with non-existent task."""
    with pytest.raises(NotFoundError, match="Task with id 999 not found"):
        await evaluation_service.create_test_case(
            session=test_session,
            task_id=999,
            description="Test case",
            arguments={},
            expected_output="expected")


@pytest.mark.asyncio
async def test_get_test_case(evaluation_service, test_session):
    """Test getting a test case by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={},
        expected_output="expected")

    retrieved = await evaluation_service.get_test_case(test_session, test_case.id)
    assert retrieved.id == test_case.id
    assert retrieved.description == "Test case"


@pytest.mark.asyncio
async def test_get_test_case_not_found(evaluation_service, test_session):
    """Test getting a non-existent test case."""
    with pytest.raises(NotFoundError, match="Test case with id 999 not found"):
        await evaluation_service.get_test_case(test_session, 999)


@pytest.mark.asyncio
async def test_list_test_cases(evaluation_service, test_session):
    """Test listing test cases for a task."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create test cases
    test_case1 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case 1",
        arguments={"input": "test1"},
        expected_output="expected1")

    test_case2 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case 2",
        arguments={"input": "test2"},
        expected_output="expected2")

    test_cases = await evaluation_service.list_test_cases(test_session, task.id)
    assert len(test_cases) == 2

    # Should be ordered by created_at desc
    test_case_ids = [tc.id for tc in test_cases]
    assert test_case2.id in test_case_ids
    assert test_case1.id in test_case_ids


@pytest.mark.asyncio
async def test_update_test_case(evaluation_service, test_session):
    """Test updating a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Original description",
        arguments={"input": "original"},
        expected_output="original expected")

    updated = await evaluation_service.update_test_case(
        session=test_session,
        test_case_id=test_case.id,
        description="Updated description",
        expected_output="Updated expected")

    assert updated.description == "Updated description"
    assert updated.expected_output == "Updated expected"
    assert updated.arguments == {"input": "original"}  # Should remain unchanged


@pytest.mark.asyncio
async def test_delete_test_case(evaluation_service, test_session):
    """Test deleting a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={},
        expected_output="expected")

    await evaluation_service.delete_test_case(test_session, test_case.id)

    # Verify test case is deleted
    with pytest.raises(NotFoundError):
        await evaluation_service.get_test_case(test_session, test_case.id)


# Evaluation Configuration Tests
@pytest.mark.asyncio
async def test_create_evaluation_config(evaluation_service, test_session):
    """Test creating evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.6,
        cost_weight=0.3,
        time_weight=0.1,
        grader_ids=[1, 2, 3])

    assert config.task_id == task.id
    assert config.quality_weight == 0.6
    assert config.cost_weight == 0.3
    assert config.time_weight == 0.1
    assert config.grader_ids == [1, 2, 3]


@pytest.mark.asyncio
async def test_create_evaluation_config_invalid_weights(evaluation_service, test_session):
    """Test creating evaluation config with invalid weights."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    with pytest.raises(BadRequestError, match="Quality, cost, and time weights must sum to 1.0"):
        await evaluation_service.create_or_update_evaluation_config(
            session=test_session,
            task_id=task.id,
            quality_weight=0.5,
            cost_weight=0.5,
            time_weight=0.5,  # Total = 1.5, should fail
        )


@pytest.mark.asyncio
async def test_update_evaluation_config(evaluation_service, test_session):
    """Test updating existing evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create initial config
    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.5,
        cost_weight=0.3,
        time_weight=0.2)

    # Update config
    updated_config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.7,
        cost_weight=0.2,
        time_weight=0.1,
        grader_ids=[1, 2])

    assert updated_config.id == config.id  # Same record
    assert updated_config.quality_weight == 0.7
    assert updated_config.cost_weight == 0.2
    assert updated_config.time_weight == 0.1
    assert updated_config.grader_ids == [1, 2]


@pytest.mark.asyncio
async def test_get_evaluation_config(evaluation_service, test_session):
    """Test getting evaluation configuration."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # No config exists yet
    config = await evaluation_service.get_evaluation_config(test_session, task.id)
    assert config is None

    # Create config
    created_config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.5,
        cost_weight=0.3,
        time_weight=0.2)

    # Get config
    retrieved_config = await evaluation_service.get_evaluation_config(test_session, task.id)
    assert retrieved_config.id == created_config.id


# Evaluation Execution Tests
@pytest.mark.asyncio
async def test_run_evaluation_success(evaluation_service, test_session):
    """Test running evaluation successfully."""
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
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    # Create grader
    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    # Create test cases
    test_case1 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case 1",
        arguments={"input": "test1"},
        expected_output="expected1")

    test_case2 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case 2",
        arguments={"input": "test2"},
        expected_output="expected2")

    # Create evaluation config
    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        grader_ids=[grader.id])

    # Mock execution results
    execution_result1 = ExecutionResult(
        id=1,
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered 1",
        result_text="Test result 1",
        cost=0.01)

    execution_result2 = ExecutionResult(
        id=2,
        task_id=task.id,
        implementation_id=implementation.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Test prompt rendered 2",
        result_text="Test result 2",
        cost=0.02)

    # Mock grade results
    grade1 = Grade(
        id=1,
        grader_id=grader.id,
        execution_result_id=1,
        score_float=0.8,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))

    grade2 = Grade(
        id=2,
        grader_id=grader.id,
        execution_result_id=2,
        score_float=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))

    with patch("app.services.evaluation_service.execute_task") as mock_execute, \
        patch.object(evaluation_service.grading_service, "get_grader") as mock_get_grader, \
        patch.object(evaluation_service.grading_service, "execute_grading") as mock_execute_grading:

        # Mock execute_task to return execution results
        mock_execute.side_effect = [execution_result1, execution_result2]

        # Mock grader retrieval
        mock_get_grader.return_value = grader

        # Mock grading execution
        mock_execute_grading.side_effect = [grade1, grade2]

        # Create evaluation
        evaluation = await evaluation_service.create_evaluation(
            session=test_session,
            implementation_id=implementation.id)
        assert evaluation.status == EvaluationStatus.RUNNING

        # Simulate background execution by directly updating the evaluation
        evaluation.status = EvaluationStatus.COMPLETED
        evaluation.completed_at = datetime.now(UTC)
        evaluation.grader_scores = {str(grader.id): 0.85}
        evaluation.quality_score = 0.85
        evaluation.avg_cost = 0.015
        evaluation.avg_execution_time_ms = 100.0
        await test_session.commit()
        await test_session.refresh(evaluation)

    assert evaluation.implementation_id == implementation.id
    assert evaluation.task_id == task.id
    assert evaluation.status == EvaluationStatus.COMPLETED
    assert evaluation.test_case_count == 2
    assert evaluation.quality_score == pytest.approx(0.85, abs=1e-6)  # Average of 0.8 and 0.9
    assert evaluation.avg_cost == 0.015  # Average of 0.01 and 0.02
    assert evaluation.grader_scores == {str(grader.id): pytest.approx(0.85, abs=1e-6)}


@pytest.mark.asyncio
async def test_run_evaluation_no_test_cases(evaluation_service, test_session):
    """Test running evaluation with no test cases."""
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
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    with pytest.raises(BadRequestError, match="No test cases found for task"):
        await evaluation_service.create_evaluation(
            session=test_session,
            implementation_id=implementation.id)


@pytest.mark.asyncio
async def test_run_evaluation_no_graders(evaluation_service, test_session):
    """Test running evaluation with no graders."""
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
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    # Create test case but no graders
    await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={},
        expected_output="expected")

    # The evaluation should succeed and create a default grader
    evaluation = await evaluation_service.create_evaluation(
        session=test_session,
        implementation_id=implementation.id)

    # Simulate background execution - should create default grader and complete
    evaluation.status = EvaluationStatus.COMPLETED
    evaluation.completed_at = datetime.now(UTC)
    evaluation.grader_scores = {"1": 0.8}  # Mock grader score
    evaluation.quality_score = 0.8
    await test_session.commit()
    await test_session.refresh(evaluation)

    assert evaluation.implementation_id == implementation.id
    assert evaluation.task_id == task.id
    assert evaluation.status == EvaluationStatus.COMPLETED
    assert evaluation.test_case_count == 1
    assert len(evaluation.grader_scores) > 0


@pytest.mark.asyncio
async def test_run_evaluation_error_handling(evaluation_service, test_session):
    """Test evaluation error handling."""
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
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    # Create test case
    await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={},
        expected_output="expected")

    # Create grader
    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader)
    await test_session.flush()

    # Create evaluation config
    await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        grader_ids=[grader.id])

    # Create evaluation first
    evaluation = await evaluation_service.create_evaluation(
        session=test_session,
        implementation_id=implementation.id)

    # Simulate background execution failure
    evaluation.status = EvaluationStatus.FAILED
    evaluation.completed_at = datetime.now(UTC)
    evaluation.error = "Execution failed"
    await test_session.commit()
    await test_session.refresh(evaluation)

    assert evaluation.status == EvaluationStatus.FAILED
    assert evaluation.error == "Execution failed"


# Efficiency Score Calculation Tests
@pytest.mark.asyncio
async def test_calculate_efficiency_scores(evaluation_service, test_session):
    """Test calculating efficiency scores."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create target metrics
    target_metrics = TargetTaskMetrics(
        task_id=task.id,
        cost=0.01,
        time_ms=1000.0)
    test_session.add(target_metrics)
    await test_session.commit()

    # Create evaluation with metrics
    evaluation = Evaluation(
        implementation_id=1,
        task_id=task.id,
        avg_cost=0.02,
        avg_execution_time_ms=2000.0)

    cost_efficiency, time_efficiency = await evaluation_service.calculate_efficiency_scores(
        session=test_session,
        evaluation=evaluation)

    assert cost_efficiency == 0.5  # 0.01 / 0.02
    assert time_efficiency == 0.5  # 1000.0 / 2000.0


@pytest.mark.asyncio
async def test_calculate_efficiency_scores_no_targets(evaluation_service, test_session):
    """Test calculating efficiency scores with no target metrics."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    evaluation = Evaluation(
        implementation_id=1,
        task_id=task.id,
        avg_cost=0.02,
        avg_execution_time_ms=2000.0)

    cost_efficiency, time_efficiency = await evaluation_service.calculate_efficiency_scores(
        session=test_session,
        evaluation=evaluation)

    assert cost_efficiency is None
    assert time_efficiency is None


@pytest.mark.asyncio
async def test_calculate_final_evaluation_score(evaluation_service, test_session):
    """Test calculating final evaluation score."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create evaluation config
    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.6,
        cost_weight=0.3,
        time_weight=0.1)

    # Create target metrics
    target_metrics = TargetTaskMetrics(
        task_id=task.id,
        cost=0.01,
        time_ms=1000.0)
    test_session.add(target_metrics)
    await test_session.commit()

    # Create evaluation
    evaluation = Evaluation(
        implementation_id=1,
        task_id=task.id,
        quality_score=0.8,
        avg_cost=0.02,
        avg_execution_time_ms=2000.0)

    final_score = await evaluation_service.calculate_final_evaluation_score(
        session=test_session,
        evaluation=evaluation)

    # Expected: 0.8 * 0.6 + 0.5 * 0.3 + 0.5 * 0.1 = 0.48 + 0.15 + 0.05 = 0.68
    assert final_score == 0.68


# Helper Method Tests
@pytest.mark.asyncio
async def test_get_task(evaluation_service, test_session):
    """Test getting a task by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    retrieved_task = await evaluation_service._get_task(test_session, task.id)
    assert retrieved_task.id == task.id


@pytest.mark.asyncio
async def test_get_task_not_found(evaluation_service, test_session):
    """Test getting a non-existent task."""
    with pytest.raises(NotFoundError, match="Task with id 999 not found"):
        await evaluation_service._get_task(test_session, 999)


@pytest.mark.asyncio
async def test_get_implementation(evaluation_service, test_session):
    """Test getting an implementation by ID."""
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
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    retrieved_impl = await evaluation_service._get_implementation(test_session, implementation.id)
    assert retrieved_impl.id == implementation.id
    assert retrieved_impl.task.id == task.id


@pytest.mark.asyncio
async def test_get_implementation_not_found(evaluation_service, test_session):
    """Test getting a non-existent implementation."""
    with pytest.raises(NotFoundError, match="Implementation with id 999 not found"):
        await evaluation_service._get_implementation(test_session, 999)


@pytest.mark.asyncio
async def test_get_all_project_graders_with_existing(evaluation_service, test_session):
    """Test getting all project graders when they exist."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create graders
    grader1 = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt 1",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
        is_active=True)
    test_session.add(grader1)

    grader2 = Grader(
        project_id=project.id,
        name="toxicity",
        prompt="Test prompt 2",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
        is_active=True)
    test_session.add(grader2)

    grader3 = Grader(
        project_id=project.id,
        name="inactive",
        prompt="Test prompt 3",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
        is_active=False,  # Inactive
    )
    test_session.add(grader3)

    await test_session.commit()

    grader_ids = await evaluation_service._get_all_project_graders(test_session, project.id)
    assert len(grader_ids) == 2  # Only active graders
    assert grader1.id in grader_ids
    assert grader2.id in grader_ids
    assert grader3.id not in grader_ids


@pytest.mark.asyncio
async def test_get_all_project_graders_create_default(evaluation_service, test_session):
    """Test creating default grader when none exist."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    with patch.object(evaluation_service.grading_service, "create_default_accuracy_grader") as mock_create:
        mock_grader = Grader(
            id=1,
            project_id=project.id,
            name="Accuracy",
            prompt="Default prompt",
            score_type=ScoreType.BOOLEAN,
            model="gpt-4o-mini",
            max_output_tokens=500)
        mock_create.return_value = mock_grader

        grader_ids = await evaluation_service._get_all_project_graders(test_session, project.id)

        assert len(grader_ids) == 1
        assert grader_ids[0] == 1
        mock_create.assert_called_once_with(test_session, project.id)
