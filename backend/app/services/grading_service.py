"""Service layer for grading operations.

This module encapsulates grading logic including grader execution,
prompt rendering, and database interactions.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import ScoreType
from app.models.evaluation import Grade, Grader
from app.models.executions import ExecutionResult
from app.models.traces import Trace
from app.schemas.traces import OutputItem, OutputMessageItem
from app.services.executor import LLMExecutor


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


class GradingService:
    """Service class for managing graders and grades."""

    def __init__(self, settings: Settings):
        """Initialize the grading service with settings."""
        self.settings = settings

    def _extract_text_from_output_items(self, output_items: list) -> str:
        """Extract text content from trace output items.

        Args:
            output_items: List of TraceOutputItem objects

        Returns:
            Extracted text content or empty string

        """
        if not output_items:
            return ""

        # Try to extract text from message output items
        for item in output_items:
            if item.type == "message":
                content = item.data.get("content", [])
                if content:
                    for content_part in content:
                        if content_part.get("type") == "text":
                            text = content_part.get("text")
                            if text:
                                return text

        # If no text found, try to serialize the output items as JSON
        try:
            return json.dumps(
                [{"type": item.type, **item.data} for item in output_items],
            )
        except Exception:
            return ""

    async def create_grader(
        self,
        session: AsyncSession,
        project_id: int,
        name: str,
        prompt: str,
        score_type: ScoreType,
        model: str,
        max_output_tokens: int,
        description: str | None = None,
        temperature: float | None = None,
        reasoning: dict[str, Any] | None = None,
        response_schema: dict[str, Any] | None = None,
        is_active: bool = True,
    ) -> Grader:
        """Create a new grader."""
        grader = Grader(
            project_id=project_id,
            name=name,
            description=description,
            prompt=prompt,
            score_type=score_type,
            model=model,
            temperature=temperature,
            reasoning=reasoning,
            response_schema=response_schema,
            max_output_tokens=max_output_tokens,
            is_active=is_active,
        )

        session.add(grader)
        await session.commit()
        await session.refresh(grader)

        return grader

    async def get_grader(self, session: AsyncSession, grader_id: int) -> Grader:
        """Get a grader by ID."""
        query = select(Grader).where(Grader.id == grader_id)
        result = await session.execute(query)
        grader = result.scalar_one_or_none()

        if not grader:
            raise NotFoundError(f"Grader with id {grader_id} not found")

        return grader

    async def list_graders(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> list[Grader]:
        """List all graders for a project."""
        query = (
            select(Grader)
            .where(Grader.project_id == project_id)
            .order_by(Grader.created_at.desc())
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_grader(
        self,
        session: AsyncSession,
        grader_id: int,
        **updates: Any,
    ) -> Grader:
        """Update a grader."""
        grader = await self.get_grader(session, grader_id)

        for key, value in updates.items():
            if value is not None and hasattr(grader, key):
                setattr(grader, key, value)

        await session.commit()
        await session.refresh(grader)

        return grader

    async def delete_grader(self, session: AsyncSession, grader_id: int) -> None:
        """Delete a grader and all associated grades."""
        grader = await self.get_grader(session, grader_id)
        await session.delete(grader)
        await session.commit()

    def _extract_text_from_output_item(self, item: OutputItem) -> str | None:
        """Extract text content from an OutputItem using schema."""
        if isinstance(item, OutputMessageItem) and item.content:
            for content_part in item.content:
                if content_part.text:
                    return content_part.text
        return None

    def _parse_grading_response(
        self,
        result_text: str | None,
        result_json: list[OutputItem] | list[dict[str, Any]] | dict[str, Any] | None,
        score_type: ScoreType,
    ) -> tuple[float | None, bool | None, str | None, float | None]:
        """Parse grading response to extract score, reasoning, and confidence.

        Returns:
            Tuple of (score_float, score_boolean, reasoning, confidence)

        """
        score_float = None
        score_boolean = None
        reasoning = None
        confidence = None

        # If we have structured JSON response
        if result_json:
            payload: dict[str, Any] | None = None
            if isinstance(result_json, dict):
                # Legacy dict format
                payload = result_json
            elif isinstance(result_json, list):
                # Parse OutputItem list - extract text and parse as JSON
                for item in result_json:
                    # Validate item as OutputItem schema
                    if isinstance(item, dict):
                        try:
                            # Try to parse as OutputMessageItem
                            parsed_item = OutputMessageItem.model_validate(item)
                        except Exception:
                            # If validation fails, treat as raw dict
                            if any(k in item for k in ("score", "reasoning", "confidence")):
                                payload = item
                                break
                            continue
                    else:
                        parsed_item = item

                    # Extract text from OutputMessageItem
                    text = self._extract_text_from_output_item(parsed_item)
                    if text:
                        try:
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                payload = parsed
                                break
                        except json.JSONDecodeError:
                            pass
            if payload:
                if score_type == ScoreType.FLOAT:
                    score_float = payload.get("score")
                elif score_type == ScoreType.BOOLEAN:
                    score_boolean = payload.get("score")

                reasoning = payload.get("reasoning")
                confidence = payload.get("confidence")

        # Fallback to text parsing if no JSON
        elif result_text:
            try:
                # Try to parse as JSON
                parsed = json.loads(result_text)
                if score_type == ScoreType.FLOAT:
                    score_float = parsed.get("score")
                elif score_type == ScoreType.BOOLEAN:
                    score_boolean = parsed.get("score")

                reasoning = parsed.get("reasoning")
                confidence = parsed.get("confidence")
            except json.JSONDecodeError:
                # If not JSON, treat entire text as reasoning and try to extract score
                reasoning = result_text

                # Simple score extraction from text
                if score_type == ScoreType.BOOLEAN:
                    text_lower = result_text.lower()
                    if (
                        "true" in text_lower
                        or "pass" in text_lower
                        or "yes" in text_lower
                    ):
                        score_boolean = True
                    elif (
                        "false" in text_lower
                        or "fail" in text_lower
                        or "no" in text_lower
                    ):
                        score_boolean = False

        return score_float, score_boolean, reasoning, confidence

    async def execute_grading(
        self,
        session: AsyncSession,
        grader_id: int,
        trace_id: int | None = None,
        execution_result_id: int | None = None,
        test_case_id: int | None = None,
    ) -> Grade:
        """Execute grading for a trace or execution result.

        Args:
            session: Database session
            grader_id: ID of the grader to use
            trace_id: ID of trace to grade (mutually exclusive with execution_result_id)
            execution_result_id: ID of execution result to grade (mutually exclusive with trace_id)
            test_case_id: Optional ID of test case to get expected output from

        Returns:
            Grade object with results

        """
        # Validate exactly one target
        if (trace_id is None) == (execution_result_id is None):
            raise BadRequestError(
                "Specify exactly one of trace_id or execution_result_id",
            )

        # Load grader
        grader = await self.get_grader(session, grader_id)

        if not grader.is_active:
            raise BadRequestError(f"Grader {grader_id} is not active")

        # Load target with relationships
        trace = None
        execution_result = None

        if trace_id:
            from sqlalchemy.orm import selectinload

            from app.models.tasks import Implementation as ImpModel

            query = (
                select(Trace)
                .options(
                    selectinload(Trace.implementation).selectinload(ImpModel.task),
                    selectinload(Trace.output_items),
                )
                .where(Trace.id == trace_id)
            )
            result = await session.execute(query)
            trace = result.scalar_one_or_none()
            if not trace:
                raise NotFoundError(f"Trace with id {trace_id} not found")
        else:
            from sqlalchemy.orm import selectinload

            from app.models.tasks import Implementation as ImpModel

            query = (
                select(ExecutionResult)
                .options(
                    selectinload(ExecutionResult.implementation).selectinload(
                        ImpModel.task,
                    ),
                    selectinload(ExecutionResult.task),
                )
                .where(ExecutionResult.id == execution_result_id)
            )
            result = await session.execute(query)
            execution_result = result.scalar_one_or_none()
            if not execution_result:
                raise NotFoundError(
                    f"ExecutionResult with id {execution_result_id} not found",
                )

        # Extract grading data from trace or execution result
        grading_variables = {}

        if trace:
            # Get task_prompt from implementation
            if trace.implementation:
                grading_variables["task_prompt"] = trace.implementation.prompt
            else:
                grading_variables["task_prompt"] = trace.prompt or ""

            # Get task_arguments from trace
            grading_variables["task_arguments"] = (
                json.dumps(trace.prompt_variables) if trace.prompt_variables else "{}"
            )

            # Get actual_output from trace output_items
            output_text = self._extract_text_from_output_items(trace.output_items)
            grading_variables["actual_output"] = output_text or trace.error or ""
        else:
            # Use rendered prompt from execution result (already rendered with variables)
            grading_variables["task_prompt"] = execution_result.prompt_rendered or ""

            # Get task_arguments from execution result
            grading_variables["task_arguments"] = (
                json.dumps(execution_result.arguments)
                if execution_result.arguments
                else "{}"
            )

            # Get actual_output from execution result
            if execution_result.result_json:
                grading_variables["actual_output"] = json.dumps(
                    execution_result.result_json,
                )
            else:
                grading_variables["actual_output"] = (
                    execution_result.result_text or execution_result.error or ""
                )

        # Get expected_output from test case if provided
        grading_variables["expected_output"] = ""
        if test_case_id:
            from app.models.evaluation import TestCase

            query = select(TestCase).where(TestCase.id == test_case_id)
            result = await session.execute(query)
            test_case = result.scalar_one_or_none()
            if test_case:
                grading_variables["expected_output"] = test_case.expected_output

        # Create a temporary implementation-like object for executor
        from app.models.tasks import Implementation, Task

        temp_impl = Implementation(
            task_id=0,  # Dummy value, won't be persisted
            version="grader",
            prompt=grader.prompt,
            model=grader.model,
            temperature=grader.temperature,
            reasoning=grader.reasoning,
            max_output_tokens=grader.max_output_tokens,
            temp=True,
        )

        # Create a dummy task with the grader's response_schema
        temp_task = Task(
            id=0,  # Dummy ID
            project_id=0,
            response_schema=grader.response_schema,
        )
        temp_impl.task = temp_task

        started_at = datetime.now(UTC)

        # Execute grading using LLM executor with extracted variables
        executor = LLMExecutor(self.settings)
        execution_result_base = await executor.execute(
            temp_impl,
            variables=grading_variables,
            input=None,
        )

        completed_at = datetime.now(UTC)

        # Parse response
        score_float = None
        score_boolean = None
        reasoning_text = None
        confidence = None

        if not execution_result_base.error:
            score_float, score_boolean, reasoning_text, confidence = (
                self._parse_grading_response(
                    execution_result_base.result_text,
                    execution_result_base.result_json,
                    grader.score_type,
                )
            )

        # Create grade record
        grade = Grade(
            grader_id=grader_id,
            trace_id=trace_id,
            execution_result_id=execution_result_id,
            score_float=score_float,
            score_boolean=score_boolean,
            reasoning=reasoning_text,
            confidence=confidence,
            grader_response=execution_result_base.provider_response,
            grading_started_at=started_at,
            grading_completed_at=completed_at,
            error=execution_result_base.error,
            prompt_tokens=execution_result_base.prompt_tokens,
            completion_tokens=execution_result_base.completion_tokens,
            total_tokens=execution_result_base.total_tokens,
            cached_tokens=execution_result_base.cached_tokens,
            reasoning_tokens=execution_result_base.reasoning_tokens,
            system_fingerprint=execution_result_base.system_fingerprint,
        )

        session.add(grade)
        await session.commit()
        await session.refresh(grade)

        return grade

    async def get_grade(self, session: AsyncSession, grade_id: int) -> Grade:
        """Get a grade by ID."""
        query = select(Grade).where(Grade.id == grade_id)
        result = await session.execute(query)
        grade = result.scalar_one_or_none()

        if not grade:
            raise NotFoundError(f"Grade with id {grade_id} not found")

        return grade

    async def list_grades(
        self,
        session: AsyncSession,
        trace_id: int | None = None,
        execution_result_id: int | None = None,
        grader_id: int | None = None,
    ) -> list[Grade]:
        """List grades with optional filters.

        Args:
            session: Database session
            trace_id: Optional filter by trace ID
            execution_result_id: Optional filter by execution result ID
            grader_id: Optional filter by grader ID

        Returns:
            List of grades matching the filters

        """
        query = select(Grade)

        if trace_id is not None:
            query = query.where(Grade.trace_id == trace_id)
        if execution_result_id is not None:
            query = query.where(Grade.execution_result_id == execution_result_id)
        if grader_id is not None:
            query = query.where(Grade.grader_id == grader_id)

        query = query.order_by(Grade.created_at.desc())

        result = await session.execute(query)
        grades: Sequence[Grade] = result.scalars().all()
        return list(grades)

    async def delete_grade(self, session: AsyncSession, grade_id: int) -> None:
        """Delete a grade."""
        grade = await self.get_grade(session, grade_id)
        await session.delete(grade)
        await session.commit()

    async def create_default_accuracy_grader(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> Grader:
        """Create a default accuracy grader for a project."""
        # Check if project already has an accuracy grader
        query = (
            select(Grader)
            .where(Grader.project_id == project_id)
            .where(Grader.name == "Accuracy")
        )
        result = await session.execute(query)
        existing_grader = result.scalar_one_or_none()

        if existing_grader:
            return existing_grader

        # Create default accuracy grader
        return await self.create_grader(
            session=session,
            project_id=project_id,
            name="Accuracy",
            description="Default accuracy grader that compares actual output with expected output",
            prompt="""Compare the actual output with the expected output.
Task Prompt: {{task_prompt}}
Task Arguments: {{task_arguments}}
Actual Output: {{actual_output}}
Expected Output: {{expected_output}}
""",
            score_type=ScoreType.FLOAT,
            model="gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=500,
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number", "description": "Score from 0.0 to 1.0"},
                    "reasoning": {"type": "string"},
                },
                "additionalProperties": False,
                "required": ["score", "reasoning"],
            },
        )
