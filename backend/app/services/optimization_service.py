from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.enums import MessageRole, OptimizationStatus
from app.models.evaluation import Evaluation
from app.models.optimizations import Optimization
from app.models.tasks import Implementation, Task
from app.schemas.optimizations import (
    OptimizationDashboardResponse,
    OptimizationDashboardSummary,
    OptimizationIterationDetail,
    OptimizationIterationEval,
    OptimizationIterationGraderDetail,
    OptimizationMutableField,
    OutperformingVersionItem,
)
from app.schemas.traces import MessageItem, OutputItem, OutputMessageItem
from app.services.evaluation_service import EvaluationService
from app.services.executor import LLMExecutor
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for iterative task implementation optimization using LLM agents."""

    # Constants
    DEFAULT_OPTIMIZER_TEMPERATURE = 0.7
    DEFAULT_OPTIMIZER_MAX_TOKENS = 1024
    MAX_VARIANT_ATTEMPTS_MULTIPLIER = 2
    DEFAULT_OPTIMIZER_MODEL = "gpt-4.1"
    OPTIMIZER_META_VERSION = "optimizer-meta"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.evaluation_service = EvaluationService(self.settings)
        self.pricing_service = PricingService()
        # Conversation history per task_id for agent context
        self._conversation: dict[int, list[MessageItem]] = {}

    async def create_optimization(
        self,
        session: AsyncSession,
        task_id: int,
        max_iterations: int,
        changeable_fields: list[OptimizationMutableField],
        max_consecutive_no_improvements: int = 3,
    ) -> Optimization:
        """Create an optimization record and return it immediately."""
        # Verify task exists
        task = await session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            raise ValueError(f"Task with id {task_id} not found")

        optimization = Optimization(
            task_id=task_id,
            status=OptimizationStatus.PENDING,
            max_iterations=max_iterations,
            changeable_fields=[f for f in changeable_fields],  # Convert to list of strings
            max_consecutive_no_improvements=max_consecutive_no_improvements,
            iterations_run=0,
            iterations=[],
        )
        session.add(optimization)
        await session.commit()
        await session.refresh(optimization)
        return optimization

    async def execute_optimization_in_background(
        self, optimization_id: int,
    ) -> None:
        """Execute optimization logic in the background, updating the optimization record continuously."""
        from app.database import AsyncSessionMaker

        # Create a new session for the background task
        async with AsyncSessionMaker() as session:
            try:
                # Load optimization
                optimization = await session.scalar(
                    select(Optimization).where(Optimization.id == optimization_id),
                )

                if not optimization:
                    logger.warning(f"Optimization {optimization_id} not found")
                    return

                # Update status to RUNNING
                optimization.status = OptimizationStatus.RUNNING
                optimization.started_at = datetime.now(UTC)
                await session.commit()

                # Execute the optimization loop
                await self._run_optimization_loop(
                    session=session,
                    optimization=optimization,
                    task_id=optimization.task_id,
                    max_iterations=optimization.max_iterations,
                    changeable_fields=optimization.changeable_fields,
                    max_consecutive_no_improvements=optimization.max_consecutive_no_improvements,
                )

                # Mark as completed
                optimization.status = OptimizationStatus.COMPLETED
                optimization.completed_at = datetime.now(UTC)
                await session.commit()

            except Exception as e:
                logger.exception(f"Optimization {optimization_id} failed: {e}")
                try:
                    # Try to update status using the same session if still valid
                    opt = await session.scalar(
                        select(Optimization).where(Optimization.id == optimization_id),
                    )
                    if opt:
                        opt.status = OptimizationStatus.FAILED
                        opt.error = str(e)
                        opt.completed_at = datetime.now(UTC)
                        await session.commit()
                except Exception as update_error:
                    logger.exception(f"Failed to update optimization status: {update_error}")
                    # If session is invalid, create a new one
                    async with AsyncSessionMaker() as error_session:
                        opt = await error_session.scalar(
                            select(Optimization).where(Optimization.id == optimization_id),
                        )
                        if opt:
                            opt.status = OptimizationStatus.FAILED
                            opt.error = str(e)
                            opt.completed_at = datetime.now(UTC)
                            await error_session.commit()

    async def _run_optimization_loop(
        self,
        session: AsyncSession,
        optimization: Optimization,
        task_id: int,
        max_iterations: int,
        changeable_fields: list[str],
        max_consecutive_no_improvements: int = 3,
    ) -> None:
        """Execute iterative optimization loop, updating the optimization record continuously.
        
        This is the refactored version of the original run() method.
        """
        # Load baseline implementation and score (score may be None)
        current_best_id, current_best_score = await self._load_baseline(session, task_id)

        # Persist only control fields; do not store best impl/score anymore
        await session.commit()

        iterations_completed = 0
        iteration_details: list[OptimizationIterationDetail] = []
        consecutive_no_improvements = 0

        # Reset conversation for a fresh optimization run to avoid over-constraining the agent
        self._conversation[task_id] = []
        # Provide the initial baseline to the agent context if available

        try:
            if current_best_id is not None:
                await self._append_baseline_to_conversation(
                    session=session,
                    task_id=task_id,
                    implementation_id=current_best_id,
                )
        except Exception as e:
            logger.warning(f"Failed to append initial baseline context: {e}")

        for iteration_index in range(max_iterations):
            # Refresh optimization object to ensure we have latest state
            await session.refresh(optimization)

            # Update current iteration
            optimization.current_iteration = iteration_index + 1
            await session.flush()

            # Generate a single candidate variant using the agent
            candidate_spec = await self._generate_variant(
                session=session,
                task_id=task_id,
                changeable_fields=changeable_fields,
            )

            # Persist the candidate as a new implementation
            candidate_impl_id = await self._persist_variant(
                session=session,
                task_id=task_id,
                current_implementation_id=current_best_id,
                candidate_spec=candidate_spec,
            )

            # Evaluate the candidate and collect score
            candidate_scores = await self._evaluate_implementations(
                session=session,
                implementation_ids=[candidate_impl_id] if candidate_impl_id is not None else [],
            )

            # Choose best between current and candidates
            next_best_id, next_best_score = self._select_best(
                current_best_id=current_best_id,
                current_best_score=current_best_score,
                candidate_scores=candidate_scores,
            )

            # Append evaluation feedback into conversation for future agent calls
            try:
                eval_summary_list = await self._append_evaluation_feedback_to_conversation(
                    session=session,
                    task_id=task_id,
                    implementation_ids=[candidate_impl_id] if candidate_impl_id is not None else [],
                    chosen_id=next_best_id,
                )
            except Exception as e:
                # Do not fail optimization run due to telemetry issues
                logger.warning(f"Failed to append evaluation feedback: {e}")
                eval_summary_list = []

            eval_detail: OptimizationIterationEval | None = None
            if eval_summary_list:
                eval_detail = self._convert_eval_summary_to_model(eval_summary_list[0])

            # Record iteration detail
            iteration_detail = OptimizationIterationDetail(
                iteration=iteration_index + 1,
                proposed_changes=candidate_spec or {},
                candidate_implementation_id=candidate_impl_id,
                evaluation=eval_detail,
            )
            iteration_details.append(iteration_detail)

            # Convert to dict for storage
            iteration_dict = iteration_detail.model_dump()

            # Refresh optimization before modifying to ensure session is aware of it
            await session.refresh(optimization)

            # Update optimization record with new iteration
            # Create a new list to ensure SQLAlchemy detects the change
            optimization.iterations = optimization.iterations + [iteration_dict]
            optimization.iterations_run = iteration_index + 1

            await session.commit()

            iterations_completed = iteration_index + 1

            # Check if this iteration resulted in improvement
            is_improved = self._is_improved(
                previous_score=current_best_score,
                new_score=next_best_score,
            )

            if is_improved:
                # Reset consecutive no-improvements counter on improvement
                consecutive_no_improvements = 0

                # If we found a better implementation, add it as the new baseline context for the agent
                try:
                    if next_best_id is not None and next_best_id != current_best_id:
                        await self._append_baseline_to_conversation(
                            session=session,
                            task_id=task_id,
                            implementation_id=next_best_id,
                        )
                except Exception as e:
                    logger.warning(f"Failed to append baseline context: {e}")

                current_best_id, current_best_score = next_best_id, next_best_score

            else:
                # Increment consecutive no-improvements counter
                consecutive_no_improvements += 1

                # Stop if we've hit the consecutive no-improvements limit
                if consecutive_no_improvements >= max_consecutive_no_improvements:
                    logger.info(
                        f"Stopping optimization after {consecutive_no_improvements} "
                        f"consecutive iterations without improvement (limit: {max_consecutive_no_improvements})",
                    )
                    break

        logger.info(f"Stopping optimization after max iterations: {max_iterations}")

        # Final update
        optimization.current_iteration = None
        await session.commit()

    def _convert_eval_summary_to_model(self, summary: dict[str, Any]) -> OptimizationIterationEval:
        """Convert internal evaluation summary dict to the schema model."""
        graders_raw = summary.get("graders") or []
        graders: list[OptimizationIterationGraderDetail] = []
        for g in graders_raw:
            graders.append(
                OptimizationIterationGraderDetail(
                    score=g.get("score"),
                    reasonings=g.get("reasonings") or [],
                ),
            )
        return OptimizationIterationEval(
            implementation_id=summary.get("implementation_id"),
            version=summary.get("version"),
            avg_cost=summary.get("avg_cost"),
            avg_execution_time_ms=summary.get("avg_execution_time_ms"),
            graders=graders,
        )

    async def _load_baseline(
        self, session: AsyncSession, task_id: int,
    ) -> tuple[int | None, float | None]:
        """Return (implementation_id, score) to serve as baseline.

        Contract: prefer highest evaluated implementation; fallback to production version.
        """
        # Get the task and its production version (if any)
        task = await session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            return None, None

        # Gather all implementation IDs for the task
        impl_ids: list[int] = list(
            (await session.execute(
                select(Implementation.id).where(Implementation.task_id == task_id),
            )).scalars().all(),
        )

        best_impl_id: int | None = None
        best_score: float | None = None

        # Evaluate average final scores for each implementation and pick the best
        for impl_id in impl_ids:
            stats = await self.evaluation_service.get_implementation_evaluation_stats(
                session=session, implementation_id=impl_id,
            )
            score = stats.avg_final_evaluation_score
            if score is not None and (best_score is None or score > best_score):
                best_impl_id = impl_id
                best_score = score

        # Fallback to production version if no scored implementation exists
        if best_impl_id is None:
            return task.production_version_id, None

        return best_impl_id, best_score

    async def _generate_variant(
        self,
        session: AsyncSession,
        task_id: int,
        changeable_fields: list[OptimizationMutableField],
    ) -> dict[str, Any] | None:
        """Return a single variant spec to create a new implementation using an LLM agent.

        The agent is prompted with a meta-prompt and the per-task conversation (which contains
        prior evaluation feedback). The agent returns a JSON object with field overrides from
        the allowed `changeable_fields`.
        """
        available_models = self._get_available_models()
        evaluation_weights = await self._get_evaluation_weights(session, task_id)

        variables = self._build_optimizer_variables(available_models, evaluation_weights)
        variant = await self._generate_single_variant_candidate(
            task_id=task_id,
            changeable_fields=changeable_fields,
            available_models=available_models,
            variables=variables,
        )

        self._record_variant_in_conversation(task_id, variant)
        return variant

    def _get_available_models(self) -> list[dict[str, Any]]:
        """Get list of all available models and their pricing across providers, for the optimizer agent."""
        return self.pricing_service.get_models_with_pricing()

    async def _get_evaluation_weights(
        self, session: AsyncSession, task_id: int,
    ) -> dict[str, float] | None:
        """Get evaluation weights configuration for a task."""
        cfg = await self.evaluation_service.get_evaluation_config(session, task_id)
        if cfg:
            return {
                "quality_weight": cfg.quality_weight,
                "cost_weight": cfg.cost_weight,
                "time_weight": cfg.time_weight,
            }
        return None

    def _build_optimizer_variables(
        self,
        available_models: list[dict[str, Any]],
        evaluation_weights: dict[str, float] | None,
    ) -> dict[str, Any]:
        """Build variables dict for optimizer agent execution."""
        return {
            "available_models": available_models,
            "evaluation_weights": evaluation_weights,
        }

    async def _generate_single_variant_candidate(
        self,
        task_id: int,
        changeable_fields: list[OptimizationMutableField],
        available_models: list[dict[str, Any]],
        variables: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Generate a single variant candidate by calling the optimizer agent with retry."""
        executor = LLMExecutor(self.settings)
        attempts = 0
        max_attempts = 2 * self.MAX_VARIANT_ATTEMPTS_MULTIPLIER

        while attempts < max_attempts:
            attempts += 1

            meta_impl = self._create_meta_implementation(
                changeable_fields, available_models,
            )
            execution = await executor.execute(
                meta_impl,
                variables=variables,
                input=self._conversation.get(task_id, []),
            )

            result_obj = self._parse_execution_result(execution)
            if result_obj:
                filtered_variant = self._filter_and_validate_variant(result_obj, changeable_fields)
                if filtered_variant:
                    return filtered_variant

        return None

    def _create_meta_implementation(
        self,
        changeable_fields: list[OptimizationMutableField],
        available_models: list[dict[str, Any]],
    ) -> Implementation:
        """Create a temporary meta-implementation for the optimizer agent."""
        meta_impl = Implementation(
            task_id=None,
            version=self.OPTIMIZER_META_VERSION,
            prompt=self._build_variant_meta_prompt_json(changeable_fields),
            model=self.DEFAULT_OPTIMIZER_MODEL,
            temperature=self.DEFAULT_OPTIMIZER_TEMPERATURE,
            reasoning=None,
            tools=None,
            tool_choice=None,
            max_output_tokens=self.DEFAULT_OPTIMIZER_MAX_TOKENS,
            temp=True,
        )

        temp_task = Task(
            id=None,
            project_id=None,
            response_schema=self._build_response_schema_for_fields(changeable_fields, available_models),
        )
        meta_impl.task = temp_task
        return meta_impl

    def _extract_text_from_output_item(self, item: OutputItem) -> str | None:
        """Extract text content from an OutputItem using schema."""
        if isinstance(item, OutputMessageItem) and item.content:
            for content_part in item.content:
                if content_part.text:
                    return content_part.text
        return None

    def _parse_execution_result(self, execution: Any) -> dict[str, Any] | None:
        """Parse execution result into a dict from OutputItem list or JSON text.

        Uses OutputItem schema types to properly extract JSON from OutputMessageItem content.
        """
        rj = getattr(execution, "result_json", None)

        # Handle legacy dict directly
        if isinstance(rj, dict):
            return rj

        # Handle list[OutputItem] - parse using schema types
        if isinstance(rj, list) and rj:
            for item in rj:
                # Validate item as OutputItem schema
                if isinstance(item, dict):
                    try:
                        # Try to parse as OutputMessageItem
                        parsed_item = OutputMessageItem.model_validate(item)
                    except Exception:
                        # If validation fails, check if it's a plain dict payload
                        if any(k in item for k in ("score", "reasoning", "confidence", "version", "model")):
                            return item
                        continue
                else:
                    parsed_item = item

                # Extract text from OutputMessageItem and try to parse as JSON
                text = self._extract_text_from_output_item(parsed_item)
                if text:
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass

        # Fallback: parse result_text as JSON
        rt = getattr(execution, "result_text", None)
        if isinstance(rt, str):
            try:
                parsed = json.loads(rt)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse execution result as JSON: {e}")

        return None

    def _filter_and_validate_variant(
        self, result_obj: dict[str, Any], changeable_fields: list[OptimizationMutableField],
    ) -> dict[str, Any] | None:
        """Filter to allowed fields, preserve optional 'explanation', and require at least one change."""
        allowed = set(changeable_fields)
        filtered: dict[str, Any] = {k: v for k, v in result_obj.items() if k in allowed and v is not None}
        explanation = result_obj.get("explanation")
        if isinstance(explanation, str) and explanation.strip():
            filtered["explanation"] = explanation
        # Ensure at least one real change among allowed fields
        if not any(k in allowed for k in filtered):
            return None
        return filtered

    def _is_duplicate_variant(
        self,
        variant: dict[str, Any],
        existing_variants: list[dict[str, Any]],
        changeable_fields: list[OptimizationMutableField],
    ) -> bool:
        """Check duplication ignoring non-functional fields like 'explanation'."""
        try:
            allowed = set(changeable_fields)
            def key_of(v: dict[str, Any]) -> str:
                comparable = {k: v[k] for k in v if k in allowed}
                return json.dumps(comparable, sort_keys=True)
            variant_key = key_of(variant)
            existing_keys = {key_of(v) for v in existing_variants}
            return variant_key in existing_keys
        except (TypeError, ValueError) as e:
            logger.debug(f"Failed to check variant duplication: {e}")
            return False

    def _record_variant_in_conversation(
        self, task_id: int, variant: dict[str, Any] | None,
    ) -> None:
        """Record generated single variant in the conversation history."""
        if not variant:
            return

        try:
            content_str = json.dumps({"proposed_change": variant})
            self._conversation.setdefault(task_id, []).append(
                MessageItem(role=MessageRole.ASSISTANT, content=content_str),
            )
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to record variant in conversation: {e}")

    def _build_variant_meta_prompt_json(self, changeable_fields: list[OptimizationMutableField]) -> str:
        fields_csv = ", ".join(changeable_fields)
        return (
            "You are an expert prompt and configuration optimizer. Given a baseline implementation and evaluation feedback, "
            "Your goal is to increase quality score and decrease cost and time to execute by dividing focus depending on evaluation weights."
            "After each iteration, you will be given the evaluation feedback."
            "Produce a JSON object with ONLY the fields to change, chosen from: "
            f"{fields_csv}. Do not include unchanged fields.\n\n"
            "Return ONLY a JSON object. No extra text.\n\n"
            "Available models with pricing:\n{{available_models}}\n\n"
            "Evaluation weights:\n{{evaluation_weights}}\n"
        )

    async def _append_baseline_to_conversation(
        self,
        session: AsyncSession,
        task_id: int,
        implementation_id: int,
    ) -> None:
        """Append the new best implementation details as user context for the optimizer agent."""
        impl = await session.scalar(
            select(Implementation).where(Implementation.id == implementation_id),
        )
        if not impl:
            return
        try:
            baseline_payload = {
                "implementation_id": implementation_id,
                "version": getattr(impl, "version", None),
                "prompt": getattr(impl, "prompt", None),
                "model": getattr(impl, "model", None),
                "temperature": getattr(impl, "temperature", None),
                "max_output_tokens": getattr(impl, "max_output_tokens", None),
            }
            content_str = "Current best implementation: " + json.dumps(baseline_payload)
            self._conversation.setdefault(task_id, []).append(
                MessageItem(role=MessageRole.USER, content=content_str),
            )
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to record baseline in conversation: {e}")

    def _build_response_schema_for_fields(
        self, changeable_fields: list[OptimizationMutableField], available_models: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build JSON schema for optimizer agent response based on changeable fields. available_models, if provided, should be a list of dicts with 'name', 'provider', and pricing keys."""
        properties: dict[str, Any] = {"explanation": {"type": "string", "description": "Briefly justify why the proposed changes will improve the objective."}}
        required: list[str] = ["explanation"]

        # Make all fields optional to allow partial overrides
        if "prompt" in changeable_fields:
            properties["prompt"] = {"type": "string"}
            required.append("prompt")

        if "model" in changeable_fields:
            properties["model"] = (
                {"type": "string", "enum": [m["name"] for m in available_models]}
                if available_models is not None else {"type": "string"}
            )
            required.append("model")

        if "temperature" in changeable_fields:
            properties["temperature"] = {"type": "number", "minimum": 0.0, "maximum": 1.0}
            required.append("temperature")

        if "max_output_tokens" in changeable_fields:
            properties["max_output_tokens"] = {"type": "integer", "minimum": 1}
            required.append("max_output_tokens")

        return {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
            "required": required,
        }

    async def _persist_variant(
        self,
        session: AsyncSession,
        task_id: int,
        current_implementation_id: int | None,
        candidate_spec: dict[str, Any] | None,
    ) -> int | None:
        """Persist a single variant spec as a new Implementation and return its ID (or None).

        Unspecified fields inherit from the current implementation when provided.
        If no current implementation is available, unspecified required fields
        must be present in the spec, otherwise it is skipped.
        """
        if not candidate_spec:
            return None

        current_impl = await self._load_current_implementation(session, current_implementation_id)
        next_minor = await self._calculate_next_minor_version(session, task_id, current_impl)
        major = self._parse_major_version(current_impl.version if current_impl else None)

        implementation = self._create_implementation_from_spec(
            candidate_spec, current_impl, task_id, major, next_minor,
        )

        if implementation is None:
            return None

        session.add(implementation)
        await session.flush()
        await session.commit()
        return implementation.id

    async def _load_current_implementation(
        self, session: AsyncSession, implementation_id: int | None,
    ) -> Implementation | None:
        """Load current implementation for field inheritance."""
        if implementation_id is None:
            return None
        return await session.scalar(
            select(Implementation).where(Implementation.id == implementation_id),
        )

    def _parse_major_version(self, version: str | None) -> int:
        """Parse major version number from version string."""
        if not version:
            return 0
        parts = str(version).split(".")
        try:
            return int(parts[0])
        except (ValueError, TypeError):
            return 0

    def _parse_minor_version(self, version: str, expected_major: int) -> int | None:
        """Parse minor version if major version matches expected."""
        parts = str(version).split(".")
        if not parts:
            return None

        try:
            major_part = int(parts[0])
        except (ValueError, TypeError):
            return None

        if major_part != expected_major or len(parts) < 2:
            return None

        try:
            return int(parts[1])
        except (ValueError, TypeError):
            return None

    async def _calculate_next_minor_version(
        self, session: AsyncSession, task_id: int, current_impl: Implementation | None,
    ) -> int:
        """Calculate the next minor version number for new implementations."""
        major = self._parse_major_version(current_impl.version if current_impl else None)

        existing_versions = list(
            (await session.execute(
                select(Implementation.version).where(Implementation.task_id == task_id),
            )).scalars().all(),
        )

        max_minor = 0
        for version in existing_versions:
            minor = self._parse_minor_version(version, major)
            if minor is not None and minor > max_minor:
                max_minor = minor

        return max_minor + 1

    def _create_implementation_from_spec(
        self,
        spec: dict[str, Any],
        current_impl: Implementation | None,
        task_id: int,
        major: int,
        minor: int,
    ) -> Implementation | None:
        """Create an Implementation from a variant spec with field inheritance."""
        # Inherit or extract required fields
        prompt = spec.get("prompt") or (current_impl.prompt if current_impl else None)
        model = spec.get("model") or (current_impl.model if current_impl else None)
        max_output_tokens = spec.get("max_output_tokens") or (
            current_impl.max_output_tokens if current_impl else None
        )

        # Skip if required fields are missing
        if prompt is None or model is None or max_output_tokens is None:
            logger.warning(f"Skipping variant due to missing required fields: {spec}")
            return None

        return Implementation(
            task_id=task_id,
            version=f"{major}.{minor}",
            prompt=prompt,
            model=model,
            temperature=spec.get("temperature", current_impl.temperature if current_impl else None),
            reasoning=spec.get("reasoning", current_impl.reasoning if current_impl else None),
            tools=spec.get("tools", current_impl.tools if current_impl else None),
            tool_choice=spec.get("tool_choice", current_impl.tool_choice if current_impl else None),
            max_output_tokens=max_output_tokens,
            temp=spec.get("temp", current_impl.temp if current_impl else False),
        )

    async def _evaluate_implementations(
        self,
        session: AsyncSession,
        implementation_ids: list[int],
    ) -> dict[int, float | None]:
        """Evaluate implementations and return mapping impl_id -> final score (or None)."""
        scores: dict[int, float | None] = {}
        if not implementation_ids:
            return scores

        # Create and execute evaluations sequentially for determinism (can be parallelized later)
        created_evals: list[Evaluation] = []
        for impl_id in implementation_ids:
            evaluation = await self.evaluation_service.create_evaluation(
                session=session,
                implementation_id=impl_id,
            )
            created_evals.append(evaluation)

        # Commit to persist created evaluations before execution
        await session.commit()

        # Execute each evaluation inline by calling the background method directly
        for evaluation in created_evals:
            await self.evaluation_service.execute_evaluation_in_background(evaluation_id=evaluation.id)

        # Ensure we don't read stale objects from the identity map after background execution
        session.expire_all()

        # After execution completes, load results and compute final scores
        for impl_id in implementation_ids:
            evaluation_row = await session.scalar(
                select(Evaluation)
                .where(Evaluation.implementation_id == impl_id)
                .order_by(Evaluation.completed_at.desc().nullslast()),
            )
            if not evaluation_row:
                scores[impl_id] = None
                continue

            final_score = await self.evaluation_service.calculate_final_evaluation_score(
                session=session, evaluation=evaluation_row,
            )
            scores[impl_id] = final_score

        return scores

    async def _append_evaluation_feedback_to_conversation(
        self,
        session: AsyncSession,
        task_id: int,
        implementation_ids: list[int],
        chosen_id: int | None,
    ) -> list[dict[str, Any]]:
        """Summarize evaluation outcomes, append to conversation as a user message, and return the summary."""
        summary = await self._build_evaluation_summary(session, implementation_ids)
        content_obj = {
            "evaluation_feedback": summary,
            "chosen_implementation_id": chosen_id,
        }
        content_str = json.dumps(content_obj)
        logger.debug(f"Evaluation feedback for task {task_id}: {content_str}")
        self._conversation.setdefault(task_id, []).append(
            MessageItem(role=MessageRole.USER, content=content_str),
        )
        return summary

    async def _build_evaluation_summary(
        self, session: AsyncSession, implementation_ids: list[int],
    ) -> list[dict[str, Any]]:
        """Build summary of evaluation metrics for implementations."""
        summary: list[dict[str, Any]] = []

        for impl_id in implementation_ids:
            impl = await session.scalar(
                select(Implementation).where(Implementation.id == impl_id),
            )
            evaluation = await session.scalar(
                select(Evaluation)
                .where(Evaluation.implementation_id == impl_id)
                .order_by(Evaluation.completed_at.desc().nullslast()),
            )

            metrics = {
                "implementation_id": impl_id,
                "version": getattr(impl, "version", None),
                "avg_cost": getattr(evaluation, "avg_cost", None) if evaluation else None,
                "avg_execution_time_ms": getattr(evaluation, "avg_execution_time_ms", None) if evaluation else None,
                # Include per-grader aggregates and reasonings
                "graders": await self._get_grader_details(session, evaluation) if evaluation else [],
            }
            summary.append(metrics)

        return summary

    # final score is no longer attached to iteration evals; retained methods compute on-demand elsewhere

    async def _get_grader_details(
        self, session: AsyncSession, evaluation: Evaluation,
    ) -> list[dict[str, Any]]:
        """Aggregate per-grader average score and collect reasonings for an evaluation.

        Returns: [{ score, reasonings }]
        """
        try:
            # Fetch per-execution results including grades
            results = await self.evaluation_service.list_evaluation_results(
                session=session, evaluation_id=evaluation.id,
            )
        except Exception as e:
            logger.warning(f"Failed to list evaluation results for evaluation {evaluation.id}: {e}")
            return []

        # Group by grader_id (fallback to name for readability)
        by_grader: dict[str, dict[str, Any]] = {}
        for item in results:
            grades = getattr(item, "grades", None) or getattr(item, "grades", [])
            for g in grades:
                grader_key = str(getattr(g, "grader_id", None) or getattr(g, "grader_name", "unknown"))
                score = getattr(g, "score_float", None)
                reasoning = getattr(g, "reasoning", None)
                bucket = by_grader.setdefault(grader_key, {
                    "scores": [],
                    "reasonings": [],
                })
                if isinstance(score, (int, float)):
                    bucket["scores"].append(float(score))
                if isinstance(reasoning, str) and reasoning.strip():
                    bucket["reasonings"].append(reasoning)

        details: list[dict[str, Any]] = []
        for _, data in by_grader.items():
            scores: list[float] = data.get("scores", [])
            avg_score = sum(scores) / len(scores) if scores else None
            # Limit number of reasonings to avoid bloat
            reasonings: list[str] = data.get("reasonings", [])[:5]
            details.append({
                "score": avg_score,
                "reasonings": reasonings,
            })

        # Stable order by score descending when available
        details.sort(key=lambda d: (d.get("score") is None, -(d.get("score") or 0.0)))
        return details

    def _select_best(
        self,
        current_best_id: int | None,
        current_best_score: float | None,
        candidate_scores: dict[int, float | None],
    ) -> tuple[int | None, float | None]:
        """Choose the best by final score among current best + candidates.

        Contract: tie-breaking strategy favors current implementation (stability).
        """
        scored_candidates = self._filter_scored_candidates(candidate_scores)

        # If no candidate has a score, keep current
        if not scored_candidates:
            return current_best_id, current_best_score

        best_candidate_id, best_candidate_score = max(scored_candidates, key=lambda x: x[1])

        # Favor current implementation on ties (stability)
        if current_best_score is not None and current_best_score >= best_candidate_score:
            return current_best_id, current_best_score

        return best_candidate_id, best_candidate_score

    def _filter_scored_candidates(
        self, candidate_scores: dict[int, float | None],
    ) -> list[tuple[int, float]]:
        """Filter candidates that have numeric scores."""
        return [
            (impl_id, score)
            for impl_id, score in candidate_scores.items()
            if score is not None
        ]

    def _is_improved(
        self,
        previous_score: float | None,
        new_score: float | None,
    ) -> bool:
        """Check if new_score is strictly better than previous_score."""
        if new_score is None:
            return False
        if previous_score is None:
            return True
        return new_score > previous_score

    async def get_dashboard_metrics(
        self,
        session: AsyncSession,
        days: int = 30,
    ) -> OptimizationDashboardResponse:
        """Compute dashboard across all tasks vs production baseline (days ignored)."""
        # Count running optimizations
        running_query = select(Optimization).where(Optimization.status == OptimizationStatus.RUNNING)
        running_result = await session.execute(running_query)
        running_count = len(list(running_result.scalars().all()))

        # Iterate all tasks that have a production version set
        tasks_result = await session.execute(
            select(Task).where(Task.production_version_id.isnot(None)),
        )
        tasks: list[Task] = list(tasks_result.scalars().all())

        outperforming_versions: list[OutperformingVersionItem] = []
        score_boosts: list[float] = []
        quality_boosts: list[float] = []
        total_cost_savings = 0.0

        for task in tasks:
            production_impl_id = task.production_version_id
            if not production_impl_id:
                continue

            # Metrics for production implementation
            production_metrics = await self._get_implementation_metrics(session, production_impl_id)

            # List all other implementations for this task
            impls_res = await session.execute(
                select(Implementation.id, Implementation.version).where(Implementation.task_id == task.id),
            )
            impl_rows = list(impls_res.all())

            for impl_id, impl_version in impl_rows:
                if impl_id == production_impl_id:
                    continue

                optimized_metrics = await self._get_implementation_metrics(session, impl_id)
                if not optimized_metrics:
                    continue

                opt_score = optimized_metrics.get("final_score")
                if opt_score is None:
                    continue

                prod_score = production_metrics.get("final_score") if production_metrics else None
                if prod_score is not None and opt_score <= prod_score:
                    continue

                # Compute deltas
                score_delta = None
                quality_delta_percent = None
                cost_delta_percent = None
                time_delta_ms = None

                if opt_score is not None:
                    if prod_score is not None:
                        score_delta = opt_score - prod_score
                        if prod_score > 0:
                            score_boosts.append((score_delta / prod_score) * 100)
                    else:
                        score_delta = opt_score

                opt_quality = optimized_metrics.get("quality_score")
                prod_quality = production_metrics.get("quality_score") if production_metrics else None
                if opt_quality is not None:
                    if prod_quality is not None and prod_quality > 0:
                        quality_delta_percent = ((opt_quality - prod_quality) / prod_quality) * 100
                        quality_boosts.append(quality_delta_percent)
                    elif prod_quality is None:
                        quality_delta_percent = opt_quality * 100

                opt_cost = optimized_metrics.get("avg_cost")
                prod_cost = production_metrics.get("avg_cost") if production_metrics else None
                if opt_cost is not None and prod_cost is not None and prod_cost > 0:
                    cost_delta = prod_cost - opt_cost
                    cost_delta_percent = (cost_delta / prod_cost) * 100
                    if cost_delta > 0:
                        total_cost_savings += cost_delta * 1000  # example volume basis

                opt_time = optimized_metrics.get("avg_execution_time_ms")
                prod_time = production_metrics.get("avg_execution_time_ms") if production_metrics else None
                if opt_time is not None and prod_time is not None:
                    time_delta_ms = prod_time - opt_time

                item = OutperformingVersionItem(
                    task_id=task.id,
                    task_name=task.name,
                    production_version=production_metrics.get("version") if production_metrics else None,
                    optimized_version=impl_version,
                    production_implementation_id=production_impl_id,
                    optimized_implementation_id=impl_id,
                    score_delta=score_delta,
                    quality_delta_percent=quality_delta_percent,
                    cost_delta_percent=cost_delta_percent,
                    time_delta_ms=time_delta_ms,
                    production_score=prod_score,
                    optimized_score=opt_score,
                    production_quality=prod_quality,
                    optimized_quality=opt_quality,
                    production_cost=prod_cost,
                    optimized_cost=opt_cost,
                    production_time_ms=prod_time,
                    optimized_time_ms=opt_time,
                )
                outperforming_versions.append(item)

        avg_score_boost = sum(score_boosts) / len(score_boosts) if score_boosts else None
        avg_quality_boost = sum(quality_boosts) / len(quality_boosts) if quality_boosts else None

        summary = OptimizationDashboardSummary(
            score_boost_percent=avg_score_boost,
            quality_boost_percent=avg_quality_boost,
            money_saved=total_cost_savings if total_cost_savings > 0 else None,
            total_versions_found=len(outperforming_versions),
            running_count=running_count,
        )

        return OptimizationDashboardResponse(
            summary=summary,
            outperforming_versions=outperforming_versions,
        )

    async def _get_implementation_metrics(
        self,
        session: AsyncSession,
        implementation_id: int,
    ) -> dict[str, Any] | None:
        """Get evaluation metrics for an implementation using evaluation service.
        
        Returns dict with:
        - version: str
        - final_score: float | None
        - quality_score: float | None
        - avg_cost: float | None
        - avg_execution_time_ms: float | None
        """
        # Get the implementation to retrieve version
        impl = await session.scalar(
            select(Implementation).where(Implementation.id == implementation_id),
        )
        if not impl:
            return None

        # Use evaluation service to get aggregated stats
        stats = await self.evaluation_service.get_implementation_evaluation_stats(
            session=session,
            implementation_id=implementation_id,
        )

        # If no evaluations exist, return basic info
        if stats.evaluation_count == 0:
            return {
                "version": impl.version,
                "final_score": None,
                "quality_score": None,
                "avg_cost": None,
                "avg_execution_time_ms": None,
            }

        return {
            "version": impl.version,
            "final_score": stats.avg_final_evaluation_score,
            "quality_score": stats.avg_quality_score,
            "avg_cost": stats.avg_cost,
            "avg_execution_time_ms": stats.avg_execution_time_ms,
        }
