"""Service layer for evaluation operations.

This module encapsulates evaluation logic including test case execution,
grading, metrics calculation, and target metrics management.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
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
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.evaluation import (
    EvaluationListItem,
    EvaluationRead,
    EvaluationResultGradeItem,
    EvaluationResultItem,
    ImplementationEvaluationStats,
)
from app.services.executions_service import execute as execute_task
from app.services.grading_service import GradingService


class NotFoundError(Exception):
    """Raised when a resource is not found."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BadRequestError(Exception):
    """Raised when request validation fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EvaluationService:
    """Service class for managing evaluations and test cases."""

    def __init__(self, settings: Settings):
        """Initialize the evaluation service with settings."""
        self.settings = settings
        self.grading_service = GradingService(settings)

    # Test Case Management
    async def create_test_case(
        self,
        session: AsyncSession,
        task_id: int,
        description: str | None,
        arguments: dict[str, Any] | None,
        expected_output: list[dict[str, Any]],
    ) -> TestCase:
        """Create a new test case for a task."""
        # Verify task exists
        task = await self._get_task(session, task_id)

        test_case = TestCase(
            task_id=task_id,
            description=description,
            arguments=arguments,
            expected_output=expected_output,
        )

        session.add(test_case)
        await session.commit()
        await session.refresh(test_case)

        return test_case

    async def get_test_case(self, session: AsyncSession, test_case_id: int) -> TestCase:
        """Get a test case by ID."""
        query = select(TestCase).where(TestCase.id == test_case_id)
        result = await session.execute(query)
        test_case = result.scalar_one_or_none()

        if not test_case:
            raise NotFoundError(f"Test case with id {test_case_id} not found")

        return test_case

    async def list_test_cases(
        self,
        session: AsyncSession,
        task_id: int | None = None,
    ) -> list[TestCase]:
        """List all test cases, optionally filtered by task_id."""
        query = select(TestCase)

        if task_id is not None:
            # Verify task exists
            await self._get_task(session, task_id)
            query = query.where(TestCase.task_id == task_id)

        query = query.order_by(TestCase.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_test_case(
        self,
        session: AsyncSession,
        test_case_id: int,
        **updates: Any,
    ) -> TestCase:
        """Update a test case."""
        test_case = await self.get_test_case(session, test_case_id)

        for key, value in updates.items():
            if value is not None and hasattr(test_case, key):
                setattr(test_case, key, value)

        await session.commit()
        await session.refresh(test_case)

        return test_case

    async def delete_test_case(self, session: AsyncSession, test_case_id: int) -> None:
        """Delete a test case."""
        test_case = await self.get_test_case(session, test_case_id)
        await session.delete(test_case)
        await session.commit()

    async def create_test_cases_from_traces(
        self,
        session: AsyncSession,
        task_id: int,
        trace_ids: list[int],
    ) -> list[TestCase]:
        """Create test cases from existing traces.

        Args:
            session: Database session
            task_id: Task ID to create test cases for
            trace_ids: List of trace IDs to convert to test cases

        Returns:
            List of created test cases

        Raises:
            NotFoundError: If task or any trace not found
            BadRequestError: If trace data is invalid

        """
        # Verify task exists
        await self._get_task(session, task_id)

        # Fetch all traces with their input and output items
        query = (
            select(Trace)
            .where(Trace.id.in_(trace_ids))
            .options(
                selectinload(Trace.input_items),
                selectinload(Trace.output_items),
            )
        )
        result = await session.execute(query)
        traces = list(result.scalars().all())

        # Verify all traces were found
        if len(traces) != len(trace_ids):
            found_ids = {trace.id for trace in traces}
            missing_ids = set(trace_ids) - found_ids
            raise NotFoundError(f"Traces not found: {missing_ids}")

        test_cases = []

        for trace in traces:
            # Extract messages from input items for arguments
            messages = []
            for item in sorted(trace.input_items, key=lambda x: x.position):
                messages.append({"type": item.type.value, **item.data})

            # Build arguments dict with messages
            arguments = {"messages": messages} if messages else {}
            output = []
            for item in sorted(trace.output_items, key=lambda x: x.position):
                output.append({"type": item.type, **item.data})

            description = f"Test case from trace {trace.id}"
            if trace.started_at:
                description += f" ({trace.started_at.strftime('%Y-%m-%d %H:%M:%S')})"

            test_case = TestCase(
                task_id=task_id,
                description=description,
                arguments=arguments,
                expected_output=output,
            )

            session.add(test_case)
            test_cases.append(test_case)

        await session.commit()

        # Refresh all test cases to get their IDs
        for test_case in test_cases:
            await session.refresh(test_case)

        return test_cases

    # Evaluation Configuration Management
    async def create_or_update_evaluation_config(
        self,
        session: AsyncSession,
        task_id: int,
        quality_weight: float = 0.5,
        cost_weight: float = 0.3,
        time_weight: float = 0.2,
        grader_ids: list[int] | None = None,
    ) -> EvaluationConfig:
        """Create or update evaluation configuration for a task."""
        # Verify task exists
        task = await self._get_task(session, task_id)

        # Validate weights sum to 1.0
        if abs(quality_weight + cost_weight + time_weight - 1.0) > 0.01:
            raise BadRequestError("Quality, cost, and time weights must sum to 1.0")

        # Get graders for this project
        if grader_ids is None:
            grader_ids = await self._get_all_project_graders(session, task.project_id)

        # Check if config already exists
        query = select(EvaluationConfig).where(EvaluationConfig.task_id == task_id)
        result = await session.execute(query)
        config = result.scalar_one_or_none()

        if config:
            # Update existing config
            config.quality_weight = quality_weight
            config.cost_weight = cost_weight
            config.time_weight = time_weight
            config.grader_ids = grader_ids
        else:
            # Create new config
            config = EvaluationConfig(
                task_id=task_id,
                quality_weight=quality_weight,
                cost_weight=cost_weight,
                time_weight=time_weight,
                grader_ids=grader_ids,
            )
            session.add(config)

        await session.commit()
        await session.refresh(config)

        return config

    async def get_evaluation_config(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> EvaluationConfig | None:
        """Get evaluation configuration for a task."""
        query = select(EvaluationConfig).where(EvaluationConfig.task_id == task_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    # Evaluation Execution
    async def create_evaluation(
        self,
        session: AsyncSession,
        implementation_id: int,
    ) -> Evaluation:
        """Create an evaluation record and return it immediately."""
        # Load implementation and task
        implementation = await self._get_implementation(session, implementation_id)
        task = implementation.task

        # Load or create evaluation config
        config = await self.get_evaluation_config(session, task.id)
        if not config:
            config = await self.create_or_update_evaluation_config(session, task.id)

        # Ensure we have graders configured
        if not config.grader_ids:
            # If no graders configured, get all available graders
            grader_ids = await self._get_all_project_graders(session, task.project_id)
            if grader_ids:
                config.grader_ids = grader_ids
                await session.commit()
            else:
                raise BadRequestError("No graders available for evaluation")

        # Load test cases
        test_cases = await self.list_test_cases(session, task.id)
        if not test_cases:
            raise BadRequestError(f"No test cases found for task {task.id}")

        # Create evaluation record
        evaluation = Evaluation(
            implementation_id=implementation_id,
            task_id=task.id,
            status=EvaluationStatus.RUNNING,
            started_at=datetime.now(UTC),
            test_case_count=len(test_cases),
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)

        return evaluation

    async def execute_evaluation_in_background(
        self,
        evaluation_id: int,
    ) -> None:
        """Execute evaluation logic in the background."""
        from app.database import AsyncSessionMaker

        # Create a new session for the background task
        async with AsyncSessionMaker() as session:
            try:
                # Load evaluation
                query = select(Evaluation).where(Evaluation.id == evaluation_id)
                result = await session.execute(query)
                evaluation = result.scalar_one_or_none()

                if not evaluation:
                    return

                # Load associated data
                implementation = await self._get_implementation(
                    session,
                    evaluation.implementation_id,
                )
                task = implementation.task

                # Load evaluation config
                config = await self.get_evaluation_config(session, task.id)
                if not config:
                    config = await self.create_or_update_evaluation_config(
                        session,
                        task.id,
                    )

                # Load test cases
                test_cases = await self.list_test_cases(session, task.id)

                try:
                    # Execute test cases and collect results
                    execution_results = []
                    for test_case in test_cases:
                        # Execute implementation with test case arguments
                        execution_result = await execute_task(
                            session=session,
                            settings=self.settings,
                            implementation_id=evaluation.implementation_id,
                            arguments=test_case.arguments,
                        )
                        # Associate execution with this evaluation and test case
                        execution_result.evaluation_id = evaluation.id
                        execution_result.test_case_id = test_case.id
                        session.add(execution_result)
                        execution_results.append(execution_result)

                    # Persist associations before grading
                    await session.commit()

                    # Grade execution results
                    grader_scores = {}
                    for grader_id in config.grader_ids:
                        grader = await self.grading_service.get_grader(
                            session,
                            grader_id,
                        )
                        scores = []

                        # Iterate through execution results with matching test cases
                        for i, execution_result in enumerate(execution_results):
                            # Get matching test case for this execution result
                            test_case = test_cases[i] if i < len(test_cases) else None

                            # Create grade for this execution result with test case
                            grade = await self.grading_service.execute_grading(
                                session=session,
                                grader_id=grader_id,
                                execution_result_id=execution_result.id,
                                test_case_id=test_case.id if test_case else None,
                            )

                            # Extract score based on grader type
                            if grader.score_type == ScoreType.FLOAT:
                                if grade.score_float is not None:
                                    scores.append(grade.score_float)
                            elif grader.score_type == ScoreType.BOOLEAN:
                                if grade.score_boolean is not None:
                                    scores.append(1.0 if grade.score_boolean else 0.0)

                        # Calculate average score for this grader
                        if scores:
                            grader_scores[str(grader_id)] = statistics.mean(scores)

                    # Calculate metrics
                    quality_score = (
                        statistics.mean(grader_scores.values())
                        if grader_scores
                        else None
                    )

                    # Calculate average cost (handle empty list)
                    cost_values = [
                        r.cost for r in execution_results if r.cost is not None
                    ]
                    avg_cost = statistics.mean(cost_values) if cost_values else None

                    # Calculate average execution time (handle empty list)
                    time_values = [
                        (r.completed_at - r.started_at).total_seconds() * 1000
                        for r in execution_results
                        if r.completed_at and r.started_at
                    ]
                    avg_time_ms = statistics.mean(time_values) if time_values else None

                    # Update evaluation with stored metrics (efficiency scores calculated on-demand)
                    evaluation.status = EvaluationStatus.COMPLETED
                    evaluation.completed_at = datetime.now(UTC)
                    evaluation.grader_scores = grader_scores
                    evaluation.quality_score = quality_score
                    evaluation.avg_cost = avg_cost
                    evaluation.avg_execution_time_ms = avg_time_ms

                    # Update target metrics if this evaluation shows better performance
                    await self.calculate_target_metrics(session, task.id)

                    await session.commit()
                    await session.refresh(evaluation)

                except Exception as e:
                    # Mark evaluation as failed
                    evaluation.status = EvaluationStatus.FAILED
                    evaluation.completed_at = datetime.now(UTC)
                    evaluation.error = str(e)
                    await session.commit()
                    await session.refresh(evaluation)

            except Exception:
                await session.rollback()

    async def get_evaluation(
        self,
        session: AsyncSession,
        evaluation_id: int,
    ) -> EvaluationRead:
        """Get an evaluation by ID with calculated scores."""
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        result = await session.execute(query)
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            raise NotFoundError(f"Evaluation with id {evaluation_id} not found")

        # Calculate scores on-demand
        (
            cost_efficiency_score,
            time_efficiency_score,
        ) = await self.calculate_efficiency_scores(
            session,
            evaluation,
        )
        final_evaluation_score = await self.calculate_final_evaluation_score(
            session,
            evaluation,
        )

        # Create EvaluationRead with calculated scores
        return EvaluationRead(
            id=evaluation.id,
            implementation_id=evaluation.implementation_id,
            task_id=evaluation.task_id,
            status=evaluation.status,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
            test_case_count=evaluation.test_case_count,
            error=evaluation.error,
            grader_scores=evaluation.grader_scores,
            quality_score=evaluation.quality_score,
            avg_cost=evaluation.avg_cost,
            avg_execution_time_ms=evaluation.avg_execution_time_ms,
            cost_efficiency_score=cost_efficiency_score,
            time_efficiency_score=time_efficiency_score,
            final_evaluation_score=final_evaluation_score,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at,
        )

    async def list_evaluation_results(
        self,
        session: AsyncSession,
        evaluation_id: int,
    ) -> list[dict[str, Any]]:
        """List per-execution results for an evaluation with grades.

        Returns a list of dicts shaped like EvaluationResultItem.
        """
        # Verify evaluation exists and get task/impl
        eval_q = select(Evaluation).where(Evaluation.id == evaluation_id)
        eval_res = await session.execute(eval_q)
        evaluation = eval_res.scalar_one_or_none()
        if not evaluation:
            raise NotFoundError(f"Evaluation with id {evaluation_id} not found")

        # Get execution results linked to this evaluation_id
        exec_q = (
            select(ExecutionResult)
            .where(ExecutionResult.evaluation_id == evaluation_id)
            .options(
                selectinload(ExecutionResult.grades).selectinload(Grade.grader),
                selectinload(ExecutionResult.test_case),
            )
            .order_by(ExecutionResult.created_at.asc())
        )
        exec_res = await session.execute(exec_q)
        executions = list(exec_res.scalars().all())

        items: list[EvaluationResultItem] = []
        for er in executions:
            items.append(
                EvaluationResultItem(
                    execution_result_id=er.id,
                    test_case_id=er.test_case_id,
                    test_case_description=er.test_case.description
                    if er.test_case
                    else None,
                    arguments=er.arguments,
                    expected_output=er.test_case.expected_output
                    if er.test_case
                    else None,
                    result_text=er.result_text,
                    result_json=er.result_json,
                    error=er.error,
                    started_at=er.started_at,
                    completed_at=er.completed_at,
                    prompt_tokens=er.prompt_tokens,
                    cached_tokens=er.cached_tokens,
                    completion_tokens=er.completion_tokens,
                    reasoning_tokens=er.reasoning_tokens,
                    total_tokens=er.total_tokens,
                    cost=er.cost,
                    grades=[
                        EvaluationResultGradeItem(
                            id=g.id,
                            grader_id=g.grader_id,
                            grader_name=g.grader.name if g.grader else None,
                            score_float=g.score_float,
                            score_boolean=g.score_boolean,
                            reasoning=g.reasoning,
                            confidence=g.confidence,
                            grading_started_at=g.grading_started_at,
                            grading_completed_at=g.grading_completed_at,
                            error=g.error,
                            created_at=g.created_at,
                        )
                        for g in (er.grades or [])
                    ],
                ),
            )
        return items

    async def list_evaluations(
        self,
        session: AsyncSession,
        implementation_id: int | None = None,
        task_id: int | None = None,
    ) -> list[EvaluationListItem]:
        """List all evaluations, optionally filtered by implementation_id or task_id with calculated scores."""
        query = select(Evaluation).options(selectinload(Evaluation.implementation))
        if implementation_id is not None:
            query = query.where(Evaluation.implementation_id == implementation_id)
        if task_id is not None:
            query = query.where(Evaluation.task_id == task_id)
        query = query.order_by(Evaluation.created_at.desc())

        result = await session.execute(query)
        evaluations = list(result.scalars().all())

        # Calculate scores for each evaluation
        evaluations_with_scores = []
        for evaluation in evaluations:
            (
                cost_efficiency_score,
                time_efficiency_score,
            ) = await self.calculate_efficiency_scores(
                session,
                evaluation,
            )
            final_evaluation_score = await self.calculate_final_evaluation_score(
                session,
                evaluation,
            )

            evaluations_with_scores.append(
                EvaluationListItem(
                    id=evaluation.id,
                    implementation_id=evaluation.implementation_id,
                    implementation_version=evaluation.implementation.version,
                    task_id=evaluation.task_id,
                    status=evaluation.status,
                    started_at=evaluation.started_at,
                    completed_at=evaluation.completed_at,
                    test_case_count=evaluation.test_case_count,
                    error=evaluation.error,
                    quality_score=evaluation.quality_score,
                    cost_efficiency_score=cost_efficiency_score,
                    time_efficiency_score=time_efficiency_score,
                    final_evaluation_score=final_evaluation_score,
                    created_at=evaluation.created_at,
                ),
            )

        return evaluations_with_scores

    async def delete_evaluation(
        self,
        session: AsyncSession,
        evaluation_id: int,
    ) -> None:
        """Delete an evaluation."""
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        result = await session.execute(query)
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            raise NotFoundError(f"Evaluation with id {evaluation_id} not found")

        await session.delete(evaluation)
        await session.commit()

    # Target Metrics Management
    async def _get_or_create_target_metrics(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> TargetTaskMetrics | None:
        """Get or create target metrics for a task."""
        query = select(TargetTaskMetrics).where(TargetTaskMetrics.task_id == task_id)
        result = await session.execute(query)
        target_metrics = result.scalar_one_or_none()

        if not target_metrics:
            # Calculate initial targets from existing executions
            await self.calculate_target_metrics(session, task_id)
            result = await session.execute(query)
            target_metrics = result.scalar_one_or_none()

        return target_metrics

    async def calculate_target_metrics(
        self,
        session: AsyncSession,
        task_id: int,
    ) -> TargetTaskMetrics:
        """Calculate and update target metrics for a task using SQL-based outlier detection."""
        # First, verify the task exists
        task_query = select(Task).where(Task.id == task_id)
        task_result = await session.execute(task_query)
        task = task_result.scalar_one_or_none()
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")

        # Use SQL to calculate target metrics with robust outlier handling
        # This approach is more efficient and statistically robust than Python-based processing

        # First, check if we have enough data for outlier detection
        count_query = (
            select(func.count(ExecutionResult.id))
            .where(ExecutionResult.task_id == task_id)
            .where(ExecutionResult.cost.isnot(None))
            .where(ExecutionResult.completed_at.isnot(None))
            .where(ExecutionResult.started_at.isnot(None))
        )
        result = await session.execute(count_query)
        execution_count = result.scalar()

        if execution_count < 5:
            # Not enough data for robust outlier detection, use simple min
            simple_query = (
                select(
                    func.min(ExecutionResult.cost).label("best_cost"),
                    func.min(
                        func.extract(
                            "epoch",
                            ExecutionResult.completed_at - ExecutionResult.started_at,
                        )
                        * 1000,
                    ).label("best_time_ms"),
                )
                .where(ExecutionResult.task_id == task_id)
                .where(ExecutionResult.cost.isnot(None))
                .where(ExecutionResult.completed_at.isnot(None))
                .where(ExecutionResult.started_at.isnot(None))
            )
            result = await session.execute(simple_query)
            row = result.first()

            if not row or (row.best_cost is None and row.best_time_ms is None):
                # No executions to calculate from
                target_metrics = TargetTaskMetrics(task_id=task_id)
                session.add(target_metrics)
                await session.commit()
                await session.refresh(target_metrics)
                return target_metrics

            best_cost = row.best_cost
            best_time_ms = row.best_time_ms
        else:
            # Use IQR-based outlier detection for robust results
            # This is more statistically sound than simple percentile trimming
            outlier_query = """
            WITH cost_stats AS (
                SELECT
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY cost) as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cost) as q3
                FROM execution_result
                WHERE task_id = :task_id AND cost IS NOT NULL
            ),
            cost_bounds AS (
                SELECT
                    q1 - 1.5 * (q3 - q1) as lower_bound,
                    q3 + 1.5 * (q3 - q1) as upper_bound
                FROM cost_stats
            ),
            time_stats AS (
                SELECT
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000) as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000) as q3
                FROM execution_result
                WHERE task_id = :task_id AND completed_at IS NOT NULL AND started_at IS NOT NULL
            ),
            time_bounds AS (
                SELECT
                    q1 - 1.5 * (q3 - q1) as lower_bound,
                    q3 + 1.5 * (q3 - q1) as upper_bound
                FROM time_stats
            ),
            filtered_costs AS (
                SELECT MIN(er.cost) as best_cost
                FROM execution_result er
                CROSS JOIN cost_bounds cb
                WHERE er.task_id = :task_id
                    AND er.cost IS NOT NULL
                    AND er.cost BETWEEN cb.lower_bound AND cb.upper_bound
            ),
            filtered_times AS (
                SELECT MIN(EXTRACT(EPOCH FROM (er.completed_at - er.started_at)) * 1000) as best_time_ms
                FROM execution_result er
                CROSS JOIN time_bounds tb
                WHERE er.task_id = :task_id
                    AND er.completed_at IS NOT NULL
                    AND er.started_at IS NOT NULL
                    AND EXTRACT(EPOCH FROM (er.completed_at - er.started_at)) * 1000 BETWEEN tb.lower_bound AND tb.upper_bound
            )
            SELECT
                fc.best_cost,
                ft.best_time_ms
            FROM filtered_costs fc
            CROSS JOIN filtered_times ft
            """

            result = await session.execute(
                text(outlier_query),
                {"task_id": task_id},
            )
            row = result.first()

            if not row:
                # Fallback to simple min if outlier detection fails
                simple_query = (
                    select(
                        func.min(ExecutionResult.cost).label("best_cost"),
                        func.min(
                            func.extract(
                                "epoch",
                                ExecutionResult.completed_at
                                - ExecutionResult.started_at,
                            )
                            * 1000,
                        ).label("best_time_ms"),
                    )
                    .where(ExecutionResult.task_id == task_id)
                    .where(ExecutionResult.cost.isnot(None))
                    .where(ExecutionResult.completed_at.isnot(None))
                    .where(ExecutionResult.started_at.isnot(None))
                )
                result = await session.execute(simple_query)
                row = result.first()

            best_cost = row.best_cost if row else None
            best_time_ms = row.best_time_ms if row else None

        # Create or update target metrics
        query = select(TargetTaskMetrics).where(TargetTaskMetrics.task_id == task_id)
        result = await session.execute(query)
        target_metrics = result.scalar_one_or_none()

        if target_metrics:
            target_metrics.cost = best_cost
            target_metrics.time_ms = best_time_ms
            target_metrics.last_updated_at = datetime.now(UTC)
        else:
            target_metrics = TargetTaskMetrics(
                task_id=task_id,
                cost=best_cost,
                time_ms=best_time_ms,
                last_updated_at=datetime.now(UTC),
            )
            session.add(target_metrics)

        await session.commit()
        await session.refresh(target_metrics)

        return target_metrics

    # On-demand score calculation methods
    async def calculate_efficiency_scores(
        self,
        session: AsyncSession,
        evaluation: Evaluation,
    ) -> tuple[float | None, float | None]:
        """Calculate cost and time efficiency scores for an evaluation."""
        if evaluation.avg_cost is None or evaluation.avg_execution_time_ms is None:
            return None, None

        target_metrics = await self._get_or_create_target_metrics(
            session,
            evaluation.task_id,
        )
        if not target_metrics:
            return None, None

        cost_efficiency_score = None
        time_efficiency_score = None

        if target_metrics.cost is not None and evaluation.avg_cost is not None:
            # Calculate efficiency as target/actual, clamped to max 1.0
            # Score of 1.0 means equal to or better than target
            # Score < 1.0 means worse than target (proportionally)
            cost_efficiency_score = min(1.0, target_metrics.cost / evaluation.avg_cost)

        if (
            target_metrics.time_ms is not None
            and evaluation.avg_execution_time_ms is not None
        ):
            # Calculate efficiency as target/actual, clamped to max 1.0
            # Score of 1.0 means equal to or better than target
            # Score < 1.0 means worse than target (proportionally)
            time_efficiency_score = min(
                1.0,
                target_metrics.time_ms / evaluation.avg_execution_time_ms,
            )

        return cost_efficiency_score, time_efficiency_score

    async def calculate_final_evaluation_score(
        self,
        session: AsyncSession,
        evaluation: Evaluation,
    ) -> float | None:
        """Calculate final weighted evaluation score for an evaluation."""
        if evaluation.quality_score is None:
            return None

        # Get evaluation config
        config = await self.get_evaluation_config(session, evaluation.task_id)
        if not config:
            return evaluation.quality_score  # Just quality score if no config

        # Calculate efficiency scores
        (
            cost_efficiency_score,
            time_efficiency_score,
        ) = await self.calculate_efficiency_scores(
            session,
            evaluation,
        )

        # Calculate final score
        final_score = evaluation.quality_score * config.quality_weight

        if cost_efficiency_score is not None:
            final_score += cost_efficiency_score * config.cost_weight

        if time_efficiency_score is not None:
            final_score += time_efficiency_score * config.time_weight

        return final_score

    async def get_implementation_evaluation_stats(
        self,
        session: AsyncSession,
        implementation_id: int,
    ) -> ImplementationEvaluationStats:
        """Return aggregate stats for all evaluations of an implementation, optimizing avg calculation with SQL."""
        # Use a direct SQL query for averages/counts (ignoring NULLs)
        # Prepare separate queries for each metric (averages only for non-null values)
        query = select(
            func.count(Evaluation.id),  # Total count
            func.avg(Evaluation.quality_score),
            func.avg(Evaluation.avg_cost),
            func.avg(Evaluation.avg_execution_time_ms),
        ).where(Evaluation.implementation_id == implementation_id)

        result = await session.execute(query)
        count, avg_quality_score, avg_cost, avg_execution_time_ms = result.one()

        if count == 0:
            return ImplementationEvaluationStats(
                implementation_id=implementation_id,
                evaluation_count=0,
                avg_quality_score=None,
                avg_cost=None,
                avg_execution_time_ms=None,
                avg_final_evaluation_score=None,
                avg_cost_efficiency_score=None,
                avg_time_efficiency_score=None,
            )

        # Use the averaged values to construct a dummy eval object for downstream calcs
        # We fetch the first evaluation only for task_id as all share the same implementation
        first_eval = await session.scalar(
            select(Evaluation).where(Evaluation.implementation_id == implementation_id),
        )
        task_id = first_eval.task_id if first_eval else None

        avg_cost_efficiency_score = None
        avg_time_efficiency_score = None
        avg_final_evaluation_score = None

        if task_id is not None:

            class DummyEval:
                pass

            dummy = DummyEval()
            dummy.task_id = task_id
            dummy.quality_score = avg_quality_score
            dummy.avg_cost = avg_cost
            dummy.avg_execution_time_ms = avg_execution_time_ms
            # Calculate efficiency scores
            cost_eff, time_eff = await self.calculate_efficiency_scores(session, dummy)
            avg_cost_efficiency_score = cost_eff
            avg_time_efficiency_score = time_eff
            # Calculate final evaluation score
            final_score = await self.calculate_final_evaluation_score(session, dummy)
            avg_final_evaluation_score = final_score

        return ImplementationEvaluationStats(
            implementation_id=implementation_id,
            evaluation_count=count,
            avg_quality_score=avg_quality_score,
            avg_cost=avg_cost,
            avg_execution_time_ms=avg_execution_time_ms,
            avg_cost_efficiency_score=avg_cost_efficiency_score,
            avg_time_efficiency_score=avg_time_efficiency_score,
            avg_final_evaluation_score=avg_final_evaluation_score,
        )

    # Helper methods
    async def _get_task(self, session: AsyncSession, task_id: int) -> Task:
        """Get a task by ID."""
        query = select(Task).where(Task.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")

        return task

    async def _get_implementation(
        self,
        session: AsyncSession,
        implementation_id: int,
    ) -> Implementation:
        """Get an implementation by ID."""
        query = (
            select(Implementation)
            .options(selectinload(Implementation.task))
            .where(Implementation.id == implementation_id)
        )
        result = await session.execute(query)
        implementation = result.scalar_one_or_none()

        if not implementation:
            raise NotFoundError(f"Implementation with id {implementation_id} not found")

        return implementation

    async def _get_all_project_graders(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> list[int]:
        """Get all active graders for a project, creating default if none exist."""
        # Get all active graders for the project
        query = (
            select(Grader)
            .where(Grader.project_id == project_id)
            .where(Grader.is_active == True)
        )
        result = await session.execute(query)
        graders = list(result.scalars().all())

        if not graders:
            # No graders exist, create default grader
            default_grader = await self.grading_service.create_default_accuracy_grader(
                session,
                project_id,
            )
            return [default_grader.id]

        return [grader.id for grader in graders]
