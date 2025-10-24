"""Service layer for evaluation operations.

This module encapsulates evaluation logic including test case execution,
grading, metrics calculation, and target metrics management.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.enums import EvaluationStatus, ScoreType
from app.models.evaluation import (
    Evaluation,
    EvaluationConfig,
    Grader,
    TargetTaskMetrics,
    TestCase,
)
from app.models.executions import ExecutionResult
from app.models.tasks import Implementation, Task
from app.schemas.evaluation import EvaluationRead, EvaluationListItem
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
        expected_output: str,
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
        self, session: AsyncSession, task_id: int
    ) -> list[TestCase]:
        """List all test cases for a task."""
        # Verify task exists
        await self._get_task(session, task_id)
        
        query = (
            select(TestCase)
            .where(TestCase.task_id == task_id)
            .order_by(TestCase.created_at.desc())
        )
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
        self, session: AsyncSession, task_id: int
    ) -> EvaluationConfig | None:
        """Get evaluation configuration for a task."""
        query = select(EvaluationConfig).where(EvaluationConfig.task_id == task_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    # Evaluation Execution
    async def run_evaluation(
        self, session: AsyncSession, implementation_id: int
    ) -> Evaluation:
        """Run evaluation for an implementation."""
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
            started_at=datetime.now(timezone.utc),
            test_case_count=len(test_cases),
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)
        
        try:
            # Execute test cases and collect results
            execution_results = []
            for test_case in test_cases:
                # Execute implementation with test case arguments
                execution_result = await execute_task(
                    session=session,
                    settings=self.settings,
                    implementation_id=implementation_id,
                    arguments=test_case.arguments,
                )
                execution_results.append(execution_result)
            
            # Grade execution results
            grader_scores = {}
            for grader_id in config.grader_ids:
                grader = await self.grading_service.get_grader(session, grader_id)
                scores = []
                
                for execution_result in execution_results:
                    # Create grade for this execution result
                    grade = await self.grading_service.execute_grading(
                        session=session,
                        grader_id=grader_id,
                        execution_result_id=execution_result.id,
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
            quality_score = statistics.mean(grader_scores.values()) if grader_scores else None
            
            # Calculate average cost (handle empty list)
            cost_values = [r.cost for r in execution_results if r.cost is not None]
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
            evaluation.completed_at = datetime.now(timezone.utc)
            evaluation.grader_scores = grader_scores
            evaluation.quality_score = quality_score
            evaluation.avg_cost = avg_cost
            evaluation.avg_execution_time_ms = avg_time_ms
            
            # Update target metrics if this evaluation shows better performance
            await self.calculate_target_metrics(session, task.id)
            
            await session.commit()
            await session.refresh(evaluation)
            
            return evaluation
            
        except Exception as e:
            # Mark evaluation as failed
            evaluation.status = EvaluationStatus.FAILED
            evaluation.completed_at = datetime.now(timezone.utc)
            evaluation.error = str(e)
            await session.commit()
            await session.refresh(evaluation)
            raise

    async def get_evaluation(self, session: AsyncSession, evaluation_id: int) -> EvaluationRead:
        """Get an evaluation by ID with calculated scores."""
        
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        result = await session.execute(query)
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            raise NotFoundError(f"Evaluation with id {evaluation_id} not found")
        
        # Calculate scores on-demand
        cost_efficiency_score, time_efficiency_score = await self.calculate_efficiency_scores(
            session, evaluation
        )
        final_evaluation_score = await self.calculate_final_evaluation_score(session, evaluation)
        
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

    async def list_evaluations(
        self, session: AsyncSession, implementation_id: int
    ) -> list[EvaluationListItem]:
        """List all evaluations for an implementation with calculated scores."""
        
        query = (
            select(Evaluation)
            .where(Evaluation.implementation_id == implementation_id)
            .order_by(Evaluation.created_at.desc())
        )
        result = await session.execute(query)
        evaluations = list(result.scalars().all())
        
        # Calculate scores for each evaluation
        evaluations_with_scores = []
        for evaluation in evaluations:
            cost_efficiency_score, time_efficiency_score = await self.calculate_efficiency_scores(
                session, evaluation
            )
            final_evaluation_score = await self.calculate_final_evaluation_score(session, evaluation)
            
            evaluations_with_scores.append(EvaluationListItem(
                id=evaluation.id,
                implementation_id=evaluation.implementation_id,
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
            ))
        
        return evaluations_with_scores

    async def delete_evaluation(self, session: AsyncSession, evaluation_id: int) -> None:
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
        self, session: AsyncSession, task_id: int
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
        self, session: AsyncSession, task_id: int
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
                    func.min(ExecutionResult.cost).label('best_cost'),
                    func.min(
                        func.extract('epoch', ExecutionResult.completed_at - ExecutionResult.started_at) * 1000
                    ).label('best_time_ms')
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
            WITH cost_iqr AS (
                SELECT 
                    cost,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY cost) as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cost) as q3
                FROM execution_result 
                WHERE task_id = :task_id AND cost IS NOT NULL
            ),
            cost_bounds AS (
                SELECT 
                    cost,
                    q1 - 1.5 * (q3 - q1) as lower_bound,
                    q3 + 1.5 * (q3 - q1) as upper_bound
                FROM cost_iqr
            ),
            time_iqr AS (
                SELECT 
                    EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000 as time_ms,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000) as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000) as q3
                FROM execution_result 
                WHERE task_id = :task_id AND completed_at IS NOT NULL AND started_at IS NOT NULL
            ),
            time_bounds AS (
                SELECT 
                    time_ms,
                    q1 - 1.5 * (q3 - q1) as lower_bound,
                    q3 + 1.5 * (q3 - q1) as upper_bound
                FROM time_iqr
            ),
            filtered_costs AS (
                SELECT MIN(cost) as best_cost
                FROM cost_bounds 
                WHERE cost BETWEEN lower_bound AND upper_bound
            ),
            filtered_times AS (
                SELECT MIN(time_ms) as best_time_ms
                FROM time_bounds 
                WHERE time_ms BETWEEN lower_bound AND upper_bound
            )
            SELECT 
                fc.best_cost,
                ft.best_time_ms
            FROM filtered_costs fc
            CROSS JOIN filtered_times ft
            """
            
            result = await session.execute(
                text(outlier_query), 
                {"task_id": task_id}
            )
            row = result.first()
            
            if not row:
                # Fallback to simple min if outlier detection fails
                simple_query = (
                    select(
                        func.min(ExecutionResult.cost).label('best_cost'),
                        func.min(
                            func.extract('epoch', ExecutionResult.completed_at - ExecutionResult.started_at) * 1000
                        ).label('best_time_ms')
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
            target_metrics.last_updated_at = datetime.now(timezone.utc)
        else:
            target_metrics = TargetTaskMetrics(
                task_id=task_id,
                cost=best_cost,
                time_ms=best_time_ms,
                last_updated_at=datetime.now(timezone.utc),
            )
            session.add(target_metrics)
        
        await session.commit()
        await session.refresh(target_metrics)
        
        return target_metrics

    # On-demand score calculation methods
    async def calculate_efficiency_scores(
        self, session: AsyncSession, evaluation: Evaluation
    ) -> tuple[float | None, float | None]:
        """Calculate cost and time efficiency scores for an evaluation."""
        if evaluation.avg_cost is None or evaluation.avg_execution_time_ms is None:
            return None, None
        
        target_metrics = await self._get_or_create_target_metrics(session, evaluation.task_id)
        if not target_metrics:
            return None, None
        
        cost_efficiency_score = None
        time_efficiency_score = None
        
        if target_metrics.cost is not None and evaluation.avg_cost is not None:
            cost_efficiency_score = target_metrics.cost / evaluation.avg_cost
        
        if target_metrics.time_ms is not None and evaluation.avg_execution_time_ms is not None:
            time_efficiency_score = target_metrics.time_ms / evaluation.avg_execution_time_ms
        
        return cost_efficiency_score, time_efficiency_score

    async def calculate_final_evaluation_score(
        self, session: AsyncSession, evaluation: Evaluation
    ) -> float | None:
        """Calculate final weighted evaluation score for an evaluation."""
        if evaluation.quality_score is None:
            return None
        
        # Get evaluation config
        config = await self.get_evaluation_config(session, evaluation.task_id)
        if not config:
            return evaluation.quality_score  # Just quality score if no config
        
        # Calculate efficiency scores
        cost_efficiency_score, time_efficiency_score = await self.calculate_efficiency_scores(
            session, evaluation
        )
        
        # Calculate final score
        final_score = evaluation.quality_score * config.quality_weight
        
        if cost_efficiency_score is not None:
            final_score += cost_efficiency_score * config.cost_weight
        
        if time_efficiency_score is not None:
            final_score += time_efficiency_score * config.time_weight
        
        return final_score


    # Helper methods
    async def _get_task(self, session: AsyncSession, task_id: int) -> Task:
        """Get a task by ID."""
        query = select(Task).where(Task.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")
        
        return task

    async def _get_implementation(self, session: AsyncSession, implementation_id: int) -> Implementation:
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
        self, session: AsyncSession, project_id: int
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
            default_grader = await self.grading_service.create_default_accuracy_grader(session, project_id)
            return [default_grader.id]
        
        return [grader.id for grader in graders]

