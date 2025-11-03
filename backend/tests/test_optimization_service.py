"""Tests for optimization service."""

from datetime import UTC, datetime
from typing import Any

import pytest
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import OptimizationStatus
from app.models.projects import Project
from app.models.tasks import Task, Implementation
from app.services.optimization_service import OptimizationService
from app.schemas.evaluation import ImplementationEvaluationStats


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///:memory:", openai_api_key="test-key")


@pytest.fixture
def optimization_service(settings: Settings) -> OptimizationService:
    return OptimizationService(settings)


@pytest.mark.asyncio
async def test_create_optimization_success(optimization_service: OptimizationService, test_session: AsyncSession):
    # Arrange: project and task
    project = Project(name="P1")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="T1", description="", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Act
    opt = await optimization_service.create_optimization(
        session=test_session,
        task_id=task.id,
        max_iterations=3,
        changeable_fields=["prompt", "model", "temperature", "max_output_tokens"],
        max_consecutive_no_improvements=2,
    )

    # Assert
    assert opt.id is not None
    assert opt.task_id == task.id
    assert opt.status == OptimizationStatus.PENDING
    assert opt.iterations_run == 0
    assert opt.iterations == []
    assert set(opt.changeable_fields) == {"prompt", "model", "temperature", "max_output_tokens"}


@pytest.mark.asyncio
async def test_create_optimization_task_not_found(optimization_service: OptimizationService, test_session: AsyncSession):
    with pytest.raises(ValueError):
        await optimization_service.create_optimization(
            session=test_session,
            task_id=9999,
            max_iterations=2,
            changeable_fields=["prompt"],
            max_consecutive_no_improvements=1,
        )


@pytest.mark.asyncio
async def test_execute_optimization_in_background_basic_flow(optimization_service: OptimizationService, test_session: AsyncSession):
    # Arrange: baseline implementation exists
    project = Project(name="P2")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="T2", description="", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    baseline = Implementation(
        task_id=task.id,
        version="0.1",
        prompt="base",
        model="gpt-4",
        max_output_tokens=256,
    )
    test_session.add(baseline)
    await test_session.flush()

    # Create optimization row
    opt = await optimization_service.create_optimization(
        session=test_session,
        task_id=task.id,
        max_iterations=2,
        changeable_fields=["prompt", "model", "max_output_tokens", "temperature"],
        max_consecutive_no_improvements=1,
    )

    # Patch internals to avoid LLM and heavy evaluation
    # - Generate a simple variant
    async def fake_generate_single_variant_candidate(*args: Any, **kwargs: Any):
        return {"prompt": "base improved", "model": "gpt-4", "max_output_tokens": 300, "temperature": 0.5}

    # - Evaluate returns a higher score for the newly created candidate id
    async def fake_evaluate_implementations(session: AsyncSession, implementation_ids: list[int]):
        return {implementation_ids[0]: 0.9} if implementation_ids else {}

    # - Append evaluation feedback returns minimal summary
    async def fake_append_feedback(session: AsyncSession, task_id: int, implementation_ids: list[int], chosen_id: int | None):
        return [{
            "implementation_id": implementation_ids[0] if implementation_ids else None,
            "version": "0.2",
            "avg_cost": 0.01,
            "avg_execution_time_ms": 100.0,
            "graders": [{"score": 0.9, "reasonings": ["looks better"]}],
        }]

    with (
        patch.object(optimization_service, "_generate_single_variant_candidate", side_effect=fake_generate_single_variant_candidate),
        patch.object(optimization_service, "_evaluate_implementations", side_effect=fake_evaluate_implementations),
        patch.object(optimization_service, "_append_evaluation_feedback_to_conversation", side_effect=fake_append_feedback),
    ):
        # Act: run the optimization loop directly on the same test session
        await optimization_service._run_optimization_loop(
            session=test_session,
            optimization=opt,
            task_id=task.id,
            max_iterations=opt.max_iterations,
            changeable_fields=opt.changeable_fields,
            max_consecutive_no_improvements=opt.max_consecutive_no_improvements,
        )
        # Simulate what background method would do on success
        opt.status = OptimizationStatus.COMPLETED
        opt.completed_at = datetime.now(UTC)
        await test_session.commit()

    # Assert: reload and verify status and iterations
    await test_session.refresh(opt)
    assert opt.status == OptimizationStatus.COMPLETED
    assert opt.iterations_run >= 1
    assert len(opt.iterations) == opt.iterations_run
    # Check that iteration detail captured candidate info keys we expect
    latest = opt.iterations[-1]
    assert "candidate_implementation_id" in latest
    assert "proposed_changes" in latest and isinstance(latest["proposed_changes"], dict)


@pytest.mark.asyncio
async def test_get_dashboard_metrics(optimization_service: OptimizationService, test_session: AsyncSession):
    # Arrange: one task with production and one optimized version
    project = Project(name="P3")
    test_session.add(project)
    await test_session.flush()

    task = Task(name="T3", description="", project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    prod = Implementation(task_id=task.id, version="0.1", prompt="p", model="gpt-4", max_output_tokens=256)
    test_session.add(prod)
    await test_session.flush()

    task.production_version_id = prod.id
    await test_session.flush()

    opt_impl = Implementation(task_id=task.id, version="0.2", prompt="p2", model="gpt-4", max_output_tokens=256)
    test_session.add(opt_impl)
    await test_session.flush()

    # Mock evaluation stats so that optimized version outperforms production
    async def fake_get_stats(session: AsyncSession, implementation_id: int) -> ImplementationEvaluationStats:
        if implementation_id == prod.id:
            return ImplementationEvaluationStats(
                implementation_id=prod.id,
                evaluation_count=1,
                avg_quality_score=0.6,
                avg_cost=0.02,
                avg_execution_time_ms=200.0,
                avg_final_evaluation_score=0.6,
                avg_cost_efficiency_score=None,
                avg_time_efficiency_score=None,
            )
        return ImplementationEvaluationStats(
            implementation_id=opt_impl.id,
            evaluation_count=1,
            avg_quality_score=0.8,
            avg_cost=0.015,
            avg_execution_time_ms=150.0,
            avg_final_evaluation_score=0.8,
            avg_cost_efficiency_score=None,
            avg_time_efficiency_score=None,
        )

    with patch.object(optimization_service.evaluation_service, "get_implementation_evaluation_stats", side_effect=fake_get_stats):
        # Act
        dashboard = await optimization_service.get_dashboard_metrics(session=test_session, days=30)

    # Assert: one outperforming version entry
    assert dashboard.summary.total_versions_found == 1
    assert dashboard.summary.score_boost_percent is not None
    assert dashboard.summary.quality_boost_percent is not None
    assert len(dashboard.outperforming_versions) == 1
    item = dashboard.outperforming_versions[0]
    assert item.production_implementation_id == prod.id
    assert item.optimized_implementation_id == opt_impl.id
    assert item.optimized_score and item.production_score and item.optimized_score > item.production_score


