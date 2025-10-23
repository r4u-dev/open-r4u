"""Service layer for grading operations.

This module encapsulates grading logic including grader execution,
prompt rendering, and database interactions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.enums import GradeType
from app.models.evaluation import Grade, Grader
from app.models.executions import ExecutionResult
from app.models.traces import Trace
from app.services.executor import LLMExecutor
from app.schemas.traces import InputItem, MessageItem


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

    async def create_grader(
        self,
        session: AsyncSession,
        project_id: int,
        name: str,
        prompt: str,
        grade_type: GradeType,
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
            grade_type=grade_type,
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
        self, session: AsyncSession, project_id: int
    ) -> list[tuple[Grader, int]]:
        """List all graders for a project with grade counts.
        
        Returns:
            List of tuples (grader, grade_count)
        """
        query = (
            select(
                Grader,
                func.count(Grade.id).label("grade_count")
            )
            .outerjoin(Grade, Grade.grader_id == Grader.id)
            .where(Grader.project_id == project_id)
            .group_by(Grader.id)
            .order_by(Grader.created_at.desc())
        )
        
        result = await session.execute(query)
        rows = result.all()
        
        return [(row[0], row[1]) for row in rows]

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

    def _prepare_target_context(
        self,
        trace: Trace | None = None,
        execution_result: ExecutionResult | None = None,
    ) -> str:
        """Prepare context string from trace or execution result for grading."""
        if trace:
            context_parts = [
                f"Model: {trace.model}",
                f"Path: {trace.path or 'N/A'}",
                f"Result: {trace.result or 'N/A'}",
            ]
            
            if trace.error:
                context_parts.append(f"Error: {trace.error}")
            
            if trace.prompt:
                context_parts.append(f"Prompt: {trace.prompt}")
            
            # Add input items if available
            if hasattr(trace, 'input_items') and trace.input_items:
                context_parts.append("\nInput History:")
                for item in trace.input_items:
                    item_data = item.data
                    if item.type.value == "message":
                        role = item_data.get("role", "unknown")
                        content = item_data.get("content", "")
                        context_parts.append(f"  [{role}]: {content}")
            
            return "\n".join(context_parts)
        
        elif execution_result:
            context_parts = [
                f"Task ID: {execution_result.task_id}",
                f"Implementation ID: {execution_result.implementation_id}",
                f"Rendered Prompt: {execution_result.prompt_rendered}",
            ]
            
            if execution_result.result_text:
                context_parts.append(f"Result: {execution_result.result_text}")
            
            if execution_result.result_json:
                context_parts.append(f"Result JSON: {json.dumps(execution_result.result_json)}")
            
            if execution_result.error:
                context_parts.append(f"Error: {execution_result.error}")
            
            if execution_result.variables:
                context_parts.append(f"Variables: {json.dumps(execution_result.variables)}")
            
            return "\n".join(context_parts)
        
        return ""

    def _render_grading_prompt(self, grader: Grader, context: str) -> str:
        """Render grading prompt with target context.
        
        The prompt can use {{context}} placeholder for the target data.
        """
        try:
            formatted_prompt = grader.prompt.replace("{{", "{").replace("}}", "}")
            return formatted_prompt.format(context=context)
        except KeyError as e:
            raise ValueError(f"Missing variable in grading prompt template: {e}")
        except Exception as e:
            raise ValueError(f"Error rendering grading prompt: {e}")

    def _parse_grading_response(
        self,
        result_text: str | None,
        result_json: dict[str, Any] | None,
        grade_type: GradeType,
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
            if grade_type == GradeType.FLOAT:
                score_float = result_json.get("score")
            elif grade_type == GradeType.BOOLEAN:
                score_boolean = result_json.get("score")
            
            reasoning = result_json.get("reasoning")
            confidence = result_json.get("confidence")
        
        # Fallback to text parsing if no JSON
        elif result_text:
            try:
                # Try to parse as JSON
                parsed = json.loads(result_text)
                if grade_type == GradeType.FLOAT:
                    score_float = parsed.get("score")
                elif grade_type == GradeType.BOOLEAN:
                    score_boolean = parsed.get("score")
                
                reasoning = parsed.get("reasoning")
                confidence = parsed.get("confidence")
            except json.JSONDecodeError:
                # If not JSON, treat entire text as reasoning and try to extract score
                reasoning = result_text
                
                # Simple score extraction from text
                if grade_type == GradeType.BOOLEAN:
                    text_lower = result_text.lower()
                    if "true" in text_lower or "pass" in text_lower or "yes" in text_lower:
                        score_boolean = True
                    elif "false" in text_lower or "fail" in text_lower or "no" in text_lower:
                        score_boolean = False
        
        return score_float, score_boolean, reasoning, confidence

    async def execute_grading(
        self,
        session: AsyncSession,
        grader_id: int,
        trace_id: int | None = None,
        execution_result_id: int | None = None,
    ) -> Grade:
        """Execute grading for a trace or execution result.
        
        Args:
            session: Database session
            grader_id: ID of the grader to use
            trace_id: ID of trace to grade (mutually exclusive with execution_result_id)
            execution_result_id: ID of execution result to grade (mutually exclusive with trace_id)
        
        Returns:
            Grade object with results
        """
        # Validate exactly one target
        if (trace_id is None) == (execution_result_id is None):
            raise BadRequestError("Specify exactly one of trace_id or execution_result_id")
        
        # Load grader
        grader = await self.get_grader(session, grader_id)
        
        if not grader.is_active:
            raise BadRequestError(f"Grader {grader_id} is not active")
        
        # Load target
        trace = None
        execution_result = None
        
        if trace_id:
            query = select(Trace).where(Trace.id == trace_id)
            result = await session.execute(query)
            trace = result.scalar_one_or_none()
            if not trace:
                raise NotFoundError(f"Trace with id {trace_id} not found")
        else:
            query = select(ExecutionResult).where(ExecutionResult.id == execution_result_id)
            result = await session.execute(query)
            execution_result = result.scalar_one_or_none()
            if not execution_result:
                raise NotFoundError(f"ExecutionResult with id {execution_result_id} not found")
        
        # Prepare context and render prompt
        context = self._prepare_target_context(trace, execution_result)
        
        started_at = datetime.now(timezone.utc)
        
        try:
            rendered_prompt = self._render_grading_prompt(grader, context)
        except ValueError as e:
            # Create grade with error
            grade = Grade(
                grader_id=grader_id,
                trace_id=trace_id,
                execution_result_id=execution_result_id,
                grading_started_at=started_at,
                grading_completed_at=datetime.now(timezone.utc),
                error=str(e),
            )
            session.add(grade)
            await session.commit()
            await session.refresh(grade)
            return grade
        
        # Create a temporary implementation-like object for executor
        from app.models.tasks import Implementation
        
        temp_impl = Implementation(
            task_id=0,  # Dummy value, won't be persisted
            version="grader",
            prompt=rendered_prompt,
            model=grader.model,
            temperature=grader.temperature,
            reasoning=grader.reasoning,
            response_schema=grader.response_schema,
            max_output_tokens=grader.max_output_tokens,
            temp=True,
        )
        
        # Execute grading using LLM executor
        executor = LLMExecutor(self.settings)
        execution_result_base = await executor.execute(temp_impl, variables=None, input=None)
        
        completed_at = datetime.now(timezone.utc)
        
        # Parse response
        score_float = None
        score_boolean = None
        reasoning_text = None
        confidence = None
        
        if not execution_result_base.error:
            score_float, score_boolean, reasoning_text, confidence = self._parse_grading_response(
                execution_result_base.result_text,
                execution_result_base.result_json,
                grader.grade_type,
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

    async def list_grades_for_trace(
        self, session: AsyncSession, trace_id: int
    ) -> list[Grade]:
        """List all grades for a trace."""
        query = (
            select(Grade)
            .where(Grade.trace_id == trace_id)
            .order_by(Grade.created_at.desc())
        )
        result = await session.execute(query)
        grades: Sequence[Grade] = result.scalars().all()
        return list(grades)

    async def list_grades_for_execution(
        self, session: AsyncSession, execution_result_id: int
    ) -> list[Grade]:
        """List all grades for an execution result."""
        query = (
            select(Grade)
            .where(Grade.execution_result_id == execution_result_id)
            .order_by(Grade.created_at.desc())
        )
        result = await session.execute(query)
        grades: Sequence[Grade] = result.scalars().all()
        return list(grades)

    async def list_grades_for_grader(
        self, session: AsyncSession, grader_id: int
    ) -> list[Grade]:
        """List all grades produced by a grader."""
        query = (
            select(Grade)
            .where(Grade.grader_id == grader_id)
            .order_by(Grade.created_at.desc())
        )
        result = await session.execute(query)
        grades: Sequence[Grade] = result.scalars().all()
        return list(grades)

    async def delete_grade(self, session: AsyncSession, grade_id: int) -> None:
        """Delete a grade."""
        grade = await self.get_grade(session, grade_id)
        await session.delete(grade)
        await session.commit()

