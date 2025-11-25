from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import ItemType
from app.models.evaluation import EvaluationConfig, Grader
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.schemas.traces import MessageItem, TraceCreate
from app.services.traces_service import TracesService


@pytest.mark.asyncio
async def test_auto_grading_triggered_on_match(test_session: AsyncSession):
    # Setup data
    project = Project(name="test-project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id, name="test-task")
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        version="v1",
        model="gpt-4",
        prompt="System: {{system_prompt}}",
        max_output_tokens=100,
    )
    test_session.add(implementation)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="test-grader",
        prompt="grade me",
        score_type="FLOAT",
        model="gpt-4",
        max_output_tokens=100,
    )
    test_session.add(grader)
    await test_session.flush()

    config = EvaluationConfig(
        task_id=task.id,
        grader_ids=[grader.id],
    )
    test_session.add(config)
    await test_session.commit()

    # Mock settings
    settings = MagicMock(spec=Settings)

    # Mock GradingService and EvaluationService
    with (
        patch("app.services.evaluation_service.EvaluationService") as MockEvalService,
        patch("app.services.grading_service.GradingService") as MockGradingService,
    ):
        # Setup mocks
        mock_eval_service_instance = MockEvalService.return_value
        mock_eval_service_instance.get_evaluation_config = AsyncMock(
            return_value=config,
        )

        mock_grading_service_instance = MockGradingService.return_value
        mock_grading_service_instance.execute_grading = AsyncMock()

        # Initialize service
        service = TracesService(settings)

        # Create trace that matches implementation
        trace_data = TraceCreate(
            project="test-project",
            model="gpt-4",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:00:01Z",
            input=[
                MessageItem(
                    type=ItemType.MESSAGE,
                    content="System: Hello world",
                    role="system",
                ),
            ],
            output=[],
            implementation_id=implementation.id,  # Explicitly set for simplicity, or rely on auto-match
        )

        # Execute
        await service.create_trace(trace_data, test_session)

        # Verify
        mock_eval_service_instance.get_evaluation_config.assert_called_once()
        mock_grading_service_instance.execute_grading.assert_called_once()

        # Verify call args
        call_args = mock_grading_service_instance.execute_grading.call_args
        assert call_args.kwargs["grader_id"] == grader.id
        assert call_args.kwargs["trace_id"] is not None


@pytest.mark.asyncio
async def test_auto_grading_not_triggered_no_implementation(test_session: AsyncSession):
    # Setup data
    project = Project(name="test-project-2")
    test_session.add(project)
    await test_session.commit()

    # Mock settings
    settings = MagicMock(spec=Settings)

    # Mock GradingService and EvaluationService
    with (
        patch("app.services.evaluation_service.EvaluationService") as MockEvalService,
        patch("app.services.grading_service.GradingService") as MockGradingService,
    ):
        mock_eval_service_instance = MockEvalService.return_value
        mock_grading_service_instance = MockGradingService.return_value
        mock_grading_service_instance.execute_grading = AsyncMock()

        service = TracesService(settings)

        # Create trace without implementation
        trace_data = TraceCreate(
            project="test-project-2",
            model="gpt-4",
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T00:00:01Z",
            input=[
                MessageItem(
                    type=ItemType.MESSAGE,
                    content="Just a trace",
                    role="user",
                ),
            ],
            output=[],
            implementation_id=None,
        )

        # Execute
        await service.create_trace(trace_data, test_session)

        # Verify
        mock_grading_service_instance.execute_grading.assert_not_called()
