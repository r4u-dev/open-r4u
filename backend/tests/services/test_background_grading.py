from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import ItemType
from app.models.evaluation import EvaluationConfig, Grader
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.schemas.traces import MessageItem, TraceCreate
from app.services.traces_service import TracesService


@pytest.mark.asyncio
async def test_background_grading_triggered(test_session: AsyncSession):
    # Setup data
    project = Project(name="test-project-bg")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id, name="test-task-bg")
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
        trace_evaluation_percentage=100,
    )
    test_session.add(config)
    await test_session.commit()

    # Mock settings
    settings = MagicMock(spec=Settings)

    # Mock GradingService and EvaluationService
    with (
        patch("app.services.evaluation_service.EvaluationService") as MockEvalService,
        patch("app.services.grading_service.GradingService") as MockGradingService,
        patch("app.services.traces_service.AsyncSessionMaker") as MockSessionMaker,
    ):
        # Setup mocks
        mock_eval_service_instance = MockEvalService.return_value
        mock_eval_service_instance.get_evaluation_config = AsyncMock(
            return_value=config,
        )

        mock_grading_service_instance = MockGradingService.return_value
        mock_grading_service_instance.execute_grading = AsyncMock()

        # Mock session for background task
        mock_bg_session = AsyncMock(spec=AsyncSession)
        MockSessionMaker.return_value.__aenter__.return_value = mock_bg_session

        # We need to mock get(Trace, trace_id) to return a trace
        async def mock_get_trace(model, id):
            if model == TracesService:  # Not correct, but just in case
                return None
            # Return a mock trace object
            trace = MagicMock()
            trace.id = id
            trace.implementation_id = implementation.id
            return trace

        mock_bg_session.get = AsyncMock(side_effect=mock_get_trace)

        # Initialize service
        service = TracesService(settings)

        # Background tasks
        background_tasks = BackgroundTasks()

        # Create trace that matches implementation
        trace_data = TraceCreate(
            project="test-project-bg",
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
            implementation_id=implementation.id,
        )

        # Execute
        await service.create_trace(
            trace_data,
            test_session,
            background_tasks=background_tasks,
        )

        # Verify background task added
        assert len(background_tasks.tasks) == 1

        # Manually execute the background task to verify logic
        task_func = background_tasks.tasks[0].func
        task_args = background_tasks.tasks[0].args
        await task_func(*task_args)

        # Verify grading triggered
        mock_eval_service_instance.get_evaluation_config.assert_called_once()
        mock_grading_service_instance.execute_grading.assert_called_once()


@pytest.mark.asyncio
async def test_background_grading_sampling_skipped(test_session: AsyncSession):
    # Setup data
    project = Project(name="test-project-sample")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id, name="test-task-sample")
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

    config = EvaluationConfig(
        task_id=task.id,
        grader_ids=[1],  # Dummy ID
        trace_evaluation_percentage=0,  # 0% chance
    )
    test_session.add(config)
    await test_session.commit()

    # Mock settings
    settings = MagicMock(spec=Settings)

    # Mock GradingService and EvaluationService and Random
    with (
        patch("app.services.evaluation_service.EvaluationService") as MockEvalService,
        patch("app.services.grading_service.GradingService") as MockGradingService,
        patch("app.services.traces_service.AsyncSessionMaker") as MockSessionMaker,
        patch("app.services.traces_service.random.randint") as mock_randint,
    ):
        # Setup mocks
        mock_eval_service_instance = MockEvalService.return_value
        mock_eval_service_instance.get_evaluation_config = AsyncMock(
            return_value=config,
        )

        mock_grading_service_instance = MockGradingService.return_value
        mock_grading_service_instance.execute_grading = AsyncMock()

        mock_bg_session = AsyncMock(spec=AsyncSession)
        MockSessionMaker.return_value.__aenter__.return_value = mock_bg_session

        async def mock_get_trace(model, id):
            trace = MagicMock()
            trace.id = id
            trace.implementation_id = implementation.id
            return trace

        mock_bg_session.get = AsyncMock(side_effect=mock_get_trace)

        # Force random to return 50 (which is > 0)
        mock_randint.return_value = 50

        service = TracesService(settings)

        # Manually trigger the internal method to test sampling logic directly
        # We need a trace object
        trace = MagicMock()
        trace.id = 123
        trace.implementation_id = implementation.id

        await service._trigger_auto_grading(trace, mock_bg_session)

        # Verify grading NOT triggered
        mock_grading_service_instance.execute_grading.assert_not_called()
