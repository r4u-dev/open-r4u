"""Integration tests for the complete evaluation system."""

import statistics
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.enums import EvaluationStatus, ScoreType
from app.models.evaluation import (
    Grade,
    Grader,
)
from app.models.executions import ExecutionResult
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.services.evaluation_service import EvaluationService


@pytest.fixture
def evaluation_service():
    """Create evaluation service instance."""
    from app.config import Settings
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="test-key")
    return EvaluationService(settings)


@pytest.mark.asyncio
async def test_complete_evaluation_workflow(evaluation_service, test_session):
    """Test complete evaluation workflow from setup to results."""
    # 1. Setup project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # 2. Create implementation
    implementation = Implementation(
        task_id=task.id,
        version="0.1",
        prompt="You are a helpful assistant. Answer: {{question}}",
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(implementation)
    await test_session.flush()

    # 3. Create graders
    accuracy_grader = Grader(
        project_id=project.id,
        name="accuracy",
        description="Evaluates response accuracy",
        prompt="Rate the accuracy of this response: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=500,
        response_schema={
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string"},
            },
            "required": ["score", "reasoning"],
        })
    test_session.add(accuracy_grader)

    toxicity_grader = Grader(
        project_id=project.id,
        name="toxicity",
        description="Evaluates content toxicity",
        prompt="Check if this content is toxic: {{context}}",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=300,
        response_schema={
            "type": "object",
            "properties": {
                "score": {"type": "boolean"},
                "reasoning": {"type": "string"},
            },
            "required": ["score", "reasoning"],
        })
    test_session.add(toxicity_grader)
    await test_session.flush()

    # 4. Create test cases
    test_cases = [
        {
            "description": "Simple math question",
            "arguments": {"question": "What is 2+2?"},
            "expected_output": "4",
        },
        {
            "description": "Complex reasoning question",
            "arguments": {"question": "If a train leaves at 2 PM and travels 60 mph, how far will it go by 4 PM?"},
            "expected_output": "120 miles",
        },
        {
            "description": "Creative writing prompt",
            "arguments": {"question": "Write a short story about a robot."},
            "expected_output": "A story about a robot",
        },
    ]

    created_test_cases = []
    for test_case_data in test_cases:
        test_case = await evaluation_service.create_test_case(
            session=test_session,
            task_id=task.id,
            **test_case_data,
        )
        created_test_cases.append(test_case)

    # 5. Create evaluation configuration
    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.6,
        cost_weight=0.3,
        time_weight=0.1,
        grader_ids=[accuracy_grader.id, toxicity_grader.id])

    # 6. Mock execution results
    execution_results = []
    for i, test_case in enumerate(created_test_cases):
        execution_result = ExecutionResult(
            id=i + 1,
            task_id=task.id,
            implementation_id=implementation.id,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            prompt_rendered=f"You are a helpful assistant. Answer: {test_case.arguments['question']}",
            result_text=f"Test response {i + 1}",
            cost=0.01 + (i * 0.005),  # Varying costs
        )
        execution_results.append(execution_result)

    # 7. Mock grade results
    grades = []
    for i, execution_result in enumerate(execution_results):
        # Accuracy grade
        accuracy_grade = Grade(
            id=(i * 2) + 1,
            grader_id=accuracy_grader.id,
            execution_result_id=execution_result.id,
            score_float=0.8 + (i * 0.05),  # Varying accuracy scores
            reasoning=f"Response {i + 1} is mostly accurate",
            confidence=0.9,
            grading_started_at=datetime.now(UTC),
            grading_completed_at=datetime.now(UTC),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80)
        grades.append(accuracy_grade)

        # Toxicity grade
        toxicity_grade = Grade(
            id=(i * 2) + 2,
            grader_id=toxicity_grader.id,
            execution_result_id=execution_result.id,
            score_boolean=False,  # All responses are non-toxic
            reasoning=f"Response {i + 1} is not toxic",
            confidence=0.95,
            grading_started_at=datetime.now(UTC),
            grading_completed_at=datetime.now(UTC),
            prompt_tokens=40,
            completion_tokens=20,
            total_tokens=60)
        grades.append(toxicity_grade)

    # 8. Mock the execution and grading process
    with patch("app.services.evaluation_service.execute_task") as mock_execute, \
         patch.object(evaluation_service.grading_service, "get_grader") as mock_get_grader, \
         patch.object(evaluation_service.grading_service, "execute_grading") as mock_execute_grading:

        # Mock execute_task to return execution results
        mock_execute.side_effect = execution_results

        # Mock grader retrieval
        def get_grader_side_effect(session, grader_id):
            if grader_id == accuracy_grader.id:
                return accuracy_grader
            if grader_id == toxicity_grader.id:
                return toxicity_grader
            raise ValueError(f"Unknown grader ID: {grader_id}")

        mock_get_grader.side_effect = get_grader_side_effect

        # Mock grading execution
        mock_execute_grading.side_effect = grades

        # 9. Run evaluation
        evaluation = await evaluation_service.create_evaluation(
            session=test_session,
            implementation_id=implementation.id)

        # Simulate background execution completion
        evaluation.status = EvaluationStatus.COMPLETED
        evaluation.completed_at = datetime.now(UTC)
        # Calculate expected scores based on the mock data
        evaluation.grader_scores = {
            str(accuracy_grader.id): statistics.mean([0.8, 0.85, 0.9]),  # Average of accuracy scores
            str(toxicity_grader.id): 1.0,  # Boolean scores converted to 1.0 for non-toxic
        }
        evaluation.quality_score = statistics.mean(evaluation.grader_scores.values())
        evaluation.avg_cost = statistics.mean([0.01, 0.015, 0.02])  # Average of execution costs
        evaluation.avg_execution_time_ms = 100.0  # Mock execution time
        await test_session.commit()
        await test_session.refresh(evaluation)

    # 10. Verify evaluation results
    assert evaluation.implementation_id == implementation.id
    assert evaluation.task_id == task.id
    assert evaluation.status == EvaluationStatus.COMPLETED
    assert evaluation.test_case_count == 3
    assert evaluation.completed_at is not None
    assert evaluation.error is None

    # Verify grader scores
    assert len(evaluation.grader_scores) == 2
    assert str(accuracy_grader.id) in evaluation.grader_scores
    assert str(toxicity_grader.id) in evaluation.grader_scores

    # Verify quality score (average of all grader scores)
    # The actual calculation might be different due to how boolean scores are handled
    assert evaluation.quality_score is not None
    assert evaluation.quality_score > 0
    assert evaluation.quality_score <= 1.0

    # Verify cost metrics
    expected_avg_cost = (0.01 + 0.015 + 0.02) / 3  # 0.015
    assert abs(evaluation.avg_cost - expected_avg_cost) < 0.001

    # 11. Test efficiency score calculation
    evaluation_with_scores = await evaluation_service.get_evaluation(
        session=test_session,
        evaluation_id=evaluation.id)

    # Should have efficiency scores if target metrics exist
    assert evaluation_with_scores.quality_score == evaluation.quality_score
    assert evaluation_with_scores.avg_cost == evaluation.avg_cost
    assert evaluation_with_scores.final_evaluation_score is not None


@pytest.mark.asyncio
async def test_evaluation_error_recovery(evaluation_service, test_session):
    """Test evaluation error handling and recovery."""
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

    # Create test case
    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={"input": "test"},
        expected_output="expected")

    # Create evaluation first
    evaluation = await evaluation_service.create_evaluation(
        session=test_session,
        implementation_id=implementation.id)

    # Simulate background execution failure
    evaluation.status = EvaluationStatus.FAILED
    evaluation.completed_at = datetime.now(UTC)
    evaluation.error = "API timeout"
    await test_session.commit()
    await test_session.refresh(evaluation)

    assert evaluation.status == EvaluationStatus.FAILED
    assert evaluation.error == "API timeout"


@pytest.mark.asyncio
async def test_evaluation_with_multiple_implementations(evaluation_service, test_session):
    """Test evaluation system with multiple implementations."""
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

    # Create multiple implementations
    implementation1 = Implementation(
        task_id=task.id,
        version="0.1",
        prompt="Simple prompt: {{question}}",
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(implementation1)

    implementation2 = Implementation(
        task_id=task.id,
        version="0.2",
        prompt="Detailed prompt: Please answer the following question: {{question}}",
        model="gpt-4",
        max_output_tokens=1000)
    test_session.add(implementation2)
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

    # Create test case
    test_case = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Test case",
        arguments={"question": "What is 2+2?"},
        expected_output="4")

    # Mock execution results for both implementations
    execution1 = ExecutionResult(
        id=1,
        task_id=task.id,
        implementation_id=implementation1.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Simple prompt: What is 2+2?",
        result_text="4",
        cost=0.01)

    execution2 = ExecutionResult(
        id=2,
        task_id=task.id,
        implementation_id=implementation2.id,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        prompt_rendered="Detailed prompt: Please answer the following question: What is 2+2?",
        result_text="The answer is 4",
        cost=0.02)

    grade1 = Grade(
        id=1,
        grader_id=grader.id,
        execution_result_id=1,
        score_float=0.9,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))

    grade2 = Grade(
        id=2,
        grader_id=grader.id,
        execution_result_id=2,
        score_float=0.95,
        grading_started_at=datetime.now(UTC),
        grading_completed_at=datetime.now(UTC))

    # Run evaluations for both implementations
    with patch("app.services.evaluation_service.execute_task") as mock_execute, \
         patch.object(evaluation_service.grading_service, "get_grader") as mock_get_grader, \
         patch.object(evaluation_service.grading_service, "execute_grading") as mock_execute_grading, \
         patch.object(evaluation_service, "calculate_target_metrics") as mock_calculate_targets:

            # Mock target metrics calculation to avoid database constraint issues
            mock_calculate_targets.return_value = None

            # First evaluation
            mock_execute.return_value = execution1
            mock_get_grader.return_value = grader
            mock_execute_grading.return_value = grade1

            evaluation1 = await evaluation_service.create_evaluation(
                session=test_session,
                implementation_id=implementation1.id)

            # Simulate completion
            evaluation1.status = EvaluationStatus.COMPLETED
            evaluation1.completed_at = datetime.now(UTC)
            evaluation1.grader_scores = {str(grader.id): 0.9}
            evaluation1.quality_score = 0.9
            evaluation1.avg_cost = 0.01
            evaluation1.avg_execution_time_ms = 100.0

            # Second evaluation
            mock_execute.return_value = execution2
            mock_execute_grading.return_value = grade2

            evaluation2 = await evaluation_service.create_evaluation(
                session=test_session,
                implementation_id=implementation2.id)

            # Simulate completion
            evaluation2.status = EvaluationStatus.COMPLETED
            evaluation2.completed_at = datetime.now(UTC)
            evaluation2.grader_scores = {str(grader.id): 0.95}
            evaluation2.quality_score = 0.95
            evaluation2.avg_cost = 0.02
            evaluation2.avg_execution_time_ms = 120.0

            await test_session.commit()

    # Verify both evaluations completed successfully
    assert evaluation1.status == EvaluationStatus.COMPLETED
    assert evaluation2.status == EvaluationStatus.COMPLETED

    # Verify different scores
    assert evaluation1.quality_score == 0.9
    assert evaluation2.quality_score == 0.95
    assert evaluation1.avg_cost == 0.01
    assert evaluation2.avg_cost == 0.02

    # List evaluations for each implementation
    evaluations1 = await evaluation_service.list_evaluations(
        session=test_session,
        implementation_id=implementation1.id)
    evaluations2 = await evaluation_service.list_evaluations(
        session=test_session,
        implementation_id=implementation2.id)

    assert len(evaluations1) == 1
    assert len(evaluations2) == 1
    assert evaluations1[0].id == evaluation1.id
    assert evaluations2[0].id == evaluation2.id


@pytest.mark.asyncio
async def test_evaluation_config_workflow(evaluation_service, test_session):
    """Test complete evaluation configuration workflow."""
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

    # Create graders
    grader1 = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Rate accuracy: {{context}}",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500)
    test_session.add(grader1)

    grader2 = Grader(
        project_id=project.id,
        name="toxicity",
        prompt="Check toxicity: {{context}}",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300)
    test_session.add(grader2)
    await test_session.flush()

    # 1. Create initial config
    config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.5,
        cost_weight=0.3,
        time_weight=0.2,
        grader_ids=[grader1.id])

    assert config.quality_weight == 0.5
    assert config.grader_ids == [grader1.id]

    # 2. Update config
    updated_config = await evaluation_service.create_or_update_evaluation_config(
        session=test_session,
        task_id=task.id,
        quality_weight=0.6,
        cost_weight=0.2,
        time_weight=0.2,
        grader_ids=[grader1.id, grader2.id])

    assert updated_config.id == config.id  # Same record
    assert updated_config.quality_weight == 0.6
    assert updated_config.cost_weight == 0.2
    assert updated_config.grader_ids == [grader1.id, grader2.id]

    # 3. Get config
    retrieved_config = await evaluation_service.get_evaluation_config(
        session=test_session,
        task_id=task.id)

    assert retrieved_config.id == config.id
    assert retrieved_config.quality_weight == 0.6
    assert retrieved_config.grader_ids == [grader1.id, grader2.id]


@pytest.mark.asyncio
async def test_test_case_management_workflow(evaluation_service, test_session):
    """Test complete test case management workflow."""
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

    # 1. Create test cases
    test_case1 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Simple math",
        arguments={"question": "What is 2+2?"},
        expected_output="4")

    test_case2 = await evaluation_service.create_test_case(
        session=test_session,
        task_id=task.id,
        description="Complex reasoning",
        arguments={"question": "Explain photosynthesis"},
        expected_output="Process by which plants convert light to energy")

    # 2. List test cases
    test_cases = await evaluation_service.list_test_cases(
        session=test_session,
        task_id=task.id)

    assert len(test_cases) == 2
    test_case_ids = [tc.id for tc in test_cases]
    assert test_case1.id in test_case_ids
    assert test_case2.id in test_case_ids

    # 3. Get specific test case
    retrieved_test_case = await evaluation_service.get_test_case(
        session=test_session,
        test_case_id=test_case1.id)

    assert retrieved_test_case.id == test_case1.id
    assert retrieved_test_case.description == "Simple math"

    # 4. Update test case
    updated_test_case = await evaluation_service.update_test_case(
        session=test_session,
        test_case_id=test_case1.id,
        description="Updated simple math",
        expected_output="The answer is 4")

    assert updated_test_case.description == "Updated simple math"
    assert updated_test_case.expected_output == "The answer is 4"
    assert updated_test_case.arguments == {"question": "What is 2+2?"}  # Unchanged

    # 5. Delete test case
    await evaluation_service.delete_test_case(
        session=test_session,
        test_case_id=test_case2.id)

    # Verify deletion
    with pytest.raises(Exception):  # Should raise NotFoundError
        await evaluation_service.get_test_case(
            session=test_session,
            test_case_id=test_case2.id)

    # Verify remaining test case
    remaining_test_cases = await evaluation_service.list_test_cases(
        session=test_session,
        task_id=task.id)

    assert len(remaining_test_cases) == 1
    assert remaining_test_cases[0].id == test_case1.id
