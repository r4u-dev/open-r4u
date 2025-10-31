from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.optimizations import OptimizationResult, OptimizationMutableField
from app.config import get_settings, Settings
from app.services.evaluation_service import EvaluationService
from app.models.tasks import Task, Implementation
from app.models.evaluation import Evaluation
from app.services.executor import LLMExecutor
from app.services.pricing_service import PricingService


class OptimizationService:

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.evaluation_service = EvaluationService(self.settings)
        self.pricing_service = PricingService()

    async def run(
        self,
        session: AsyncSession,
        task_id: int,
        max_iterations: int,
        variants_per_iter: int,
        changeable_fields: Sequence[OptimizationMutableField],
        improvement_threshold: float,
    ) -> OptimizationResult:
        """
        Execute iterative optimization for a task's implementation and return the result summary.

        This is the orchestration only. Sub-steps are defined as contracts and
        intentionally left unimplemented for subsequent milestones.
        """
        # Load baseline implementation and score (score may be None)
        current_best_id, current_best_score = await self._load_baseline(session, task_id)

        iterations_completed = 0
        for iteration_index in range(max_iterations):
            # Generate candidate variants off the current best
            candidate_specs = await self._generate_variants(
                session=session,
                task_id=task_id,
                baseline_implementation_id=current_best_id,
                variants_per_iter=variants_per_iter,
                changeable_fields=list(changeable_fields),
            )

            # Persist candidates as new implementations, get their IDs
            candidate_impl_ids = await self._persist_variants(
                session=session,
                task_id=task_id,
                current_implementation_id=current_best_id,
                candidate_specs=candidate_specs,
            )

            # Evaluate candidates; returns mapping impl_id -> final score (or None on failure)
            candidate_scores = await self._evaluate_implementations(
                session=session,
                task_id=task_id,
                implementation_ids=candidate_impl_ids,
            )

            # Select winner among current best and new candidates
            next_best_id, next_best_score = self._select_best(
                current_best_id=current_best_id,
                current_best_score=current_best_score,
                candidate_scores=candidate_scores,
            )

            # Count this iteration as executed, regardless of improvement
            iterations_completed = iteration_index + 1

            # Stop if no improvement or improvement below threshold
            if not self._is_improved(
                previous_score=current_best_score,
                new_score=next_best_score,
                threshold=improvement_threshold,
            ):
                break

            # Accept improvement and continue
            current_best_id, current_best_score = next_best_id, next_best_score

        return OptimizationResult(
            best_implementation_id=current_best_id,
            best_score=current_best_score,
            iterations_run=iterations_completed,
        )

    async def _load_baseline(
        self, session: AsyncSession, task_id: int
    ) -> Tuple[Optional[int], Optional[float]]:
        """Return (implementation_id, score) to serve as baseline.

        Contract: prefer highest evaluated implementation; fallback to production version.
        """
        # Get the task and its production version (if any)
        task = await session.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            return None, None

        # Gather all implementation IDs for the task
        impl_ids: List[int] = list(
            (await session.execute(
                select(Implementation.id).where(Implementation.task_id == task_id)
            )).scalars().all()
        )

        best_impl_id: Optional[int] = None
        best_score: Optional[float] = None

        # Evaluate average final scores for each implementation and pick the best
        for impl_id in impl_ids:
            stats = await self.evaluation_service.get_implementation_evaluation_stats(
                session=session, implementation_id=impl_id
            )
            score = stats.avg_final_evaluation_score
            if score is not None and (best_score is None or score > best_score):
                best_impl_id = impl_id
                best_score = score

        # Fallback to production version if no scored implementation exists
        if best_impl_id is None:
            return task.production_version_id, None

        return best_impl_id, best_score

    async def _generate_variants(
        self,
        session: AsyncSession,
        task_id: int,
        baseline_implementation_id: Optional[int],
        variants_per_iter: int,
        changeable_fields: List[OptimizationMutableField],
    ) -> List[dict]:
        """Return a list of variant specs to create new implementations from.

        First step: only generate prompt variations via an AI meta-prompt. If
        `prompt` is not in changeable_fields, returns an empty list. Generates
        ONE prompt per meta-call and repeats until reaching variants_per_iter.
        """
        if variants_per_iter <= 0:
            return []

        # Load the baseline implementation to inform the meta prompt
        baseline_impl: Optional[Implementation] = None
        if baseline_implementation_id is not None:
            baseline_impl = await session.scalar(
                select(Implementation).where(Implementation.id == baseline_implementation_id)
            )
        if baseline_impl is None:
            # Fallback to production version of the task
            task = await session.scalar(select(Task).where(Task.id == task_id))
            if task and task.production_version_id:
                baseline_impl = await session.scalar(
                    select(Implementation).where(Implementation.id == task.production_version_id)
                )
        if baseline_impl is None:
            return []

        # Build a temporary meta-implementation and call repeatedly to get JSON field overrides
        # Fetch available models list for guidance/validation
        by_provider = self.pricing_service.get_available_models()
        available_models: List[str] = sorted({m for lst in by_provider.values() for m in lst})

        variables = {"baseline": {
            "prompt": baseline_impl.prompt,
            "model": baseline_impl.model,
            "temperature": baseline_impl.temperature,
            "max_output_tokens": baseline_impl.max_output_tokens,
        }, "available_models": available_models}
        variants: List[dict] = []
        executor = LLMExecutor(self.settings)

        attempts = 0
        while len(variants) < variants_per_iter and attempts < variants_per_iter * 2:
            attempts += 1
            meta_impl = Implementation(
                task_id=None,
                version="optimizer-meta",
                prompt=self._build_variant_meta_prompt_json(changeable_fields),
                model="gpt-4.1",
                temperature=0.7,
                reasoning={
                    "effort": "low",
                },
                tools=None,
                tool_choice=None,
                max_output_tokens=1024,
                temp=True,
            )
            # Dummy task schema expecting a single string
            temp_task = Task(id=None, project_id=None, response_schema=self._build_response_schema_for_fields(changeable_fields, available_models))
            meta_impl.task = temp_task

            execution = await executor.execute(meta_impl, variables=variables, input=None)
            if execution.error:
                print(f"Error executing meta-prompt: {execution.error}")
                continue

            candidate: Optional[dict] = None
            result_obj = None
            if getattr(execution, "result_json", None) and isinstance(execution.result_json, dict):
                result_obj = execution.result_json
            elif getattr(execution, "result_text", None) and isinstance(execution.result_text, str):
                try:
                    import json as _json
                    parsed = _json.loads(execution.result_text)
                    if isinstance(parsed, dict):
                        result_obj = parsed
                except Exception:
                    result_obj = None

            if isinstance(result_obj, dict):
                print(f"Result object: {result_obj}") 
                # Filter to allowed keys only and drop None values
                allowed = set(changeable_fields)
                filtered = {k: v for k, v in result_obj.items() if k in allowed and v is not None}
                # Skip empty/no-op
                if filtered:
                    # Deduplicate by stable json repr
                    try:
                        import json as _json
                        key = _json.dumps(filtered, sort_keys=True)
                        existing_keys = {
                            _json.dumps(item, sort_keys=True) for item in variants
                        }
                        if key not in existing_keys:
                            variants.append(filtered)
                    except Exception:
                        variants.append(filtered)

        return variants

    def _build_variant_meta_prompt_json(self, changeable_fields: List[OptimizationMutableField]) -> str:
        fields_csv = ", ".join(changeable_fields)
        return (
            "You are an expert prompt and configuration optimizer. Given a baseline implementation, "
            "produce a JSON object with ONLY the fields to change, chosen from: "
            f"{fields_csv}. Do not include unchanged fields.\n\n"
            "Guidelines:\n"
            "- Preserve task intent and variable placeholders.\n"
            "- Keep outputs compatible with typical LLM provider constraints.\n"
            "- Temperature in [0.0, 2.0]; max_output_tokens reasonable.\n"
            "- If changing model, pick ONLY from available_models.\n\n"
            "Return ONLY a JSON object. No extra text.\n\n"
            "Baseline:\n{{baseline}}\n\n"
            "Available models:\n{{available_models}}\n"
        )

    def _build_response_schema_for_fields(self, changeable_fields: List[OptimizationMutableField], available_models: Optional[List[str]] = None) -> dict:
        properties: dict = {}
        required: List[str] = []
        if "prompt" in changeable_fields:
            properties["prompt"] = {"type": "string"}
            required.append("prompt")
        if "model" in changeable_fields:
            if available_models:
                properties["model"] = {"type": "string", "enum": available_models}
            else:
                properties["model"] = {"type": "string"}
            required.append("model")
        if "temperature" in changeable_fields:
            properties["temperature"] = {"type": "number", "minimum": 0.0, "maximum": 1.0}
            required.append("temperature")
        if "max_output_tokens" in changeable_fields:
            properties["max_output_tokens"] = {"type": "integer", "minimum": 1}
            required.append("max_output_tokens")
        # Only allow the explicitly supported fields above
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
            "required": required,
        }
        return schema

    async def _persist_variants(
        self,
        session: AsyncSession,
        task_id: int,
        current_implementation_id: Optional[int],
        candidate_specs: List[dict],
    ) -> List[int]:
        """Persist variant specs as new Implementations and return their IDs.

        Unspecified fields inherit from the current implementation when provided.
        If no current implementation is available, unspecified required fields
        must be present in the spec, otherwise the spec is skipped.
        """
        if not candidate_specs:
            return []

        # Load current implementation for inheritance if available
        current_impl: Optional[Implementation] = None
        if current_implementation_id is not None:
            current_impl = await session.scalar(
                select(Implementation).where(Implementation.id == current_implementation_id)
            )

        # Determine major version (prefix before first dot) and next minor counter
        def parse_major(version: Optional[str]) -> int:
            if not version:
                return 0
            parts = str(version).split(".")
            try:
                return int(parts[0])
            except (ValueError, TypeError):
                return 0

        major = parse_major(current_impl.version if current_impl else None)
        existing_versions = list(
            (await session.execute(
                select(Implementation.version).where(Implementation.task_id == task_id)
            )).scalars().all()
        )

        def extract_minor_if_major_matches(version: str, major_expected: int) -> Optional[int]:
            parts = str(version).split(".")
            if not parts:
                return None
            try:
                major_part = int(parts[0])
            except (ValueError, TypeError):
                return None
            if major_part != major_expected:
                return None
            if len(parts) < 2:
                return None
            try:
                return int(parts[1])
            except (ValueError, TypeError):
                return None

        max_minor = 0
        for v in existing_versions:
            minor = extract_minor_if_major_matches(v, major)
            if minor is not None and minor > max_minor:
                max_minor = minor

        next_minor = max_minor + 1

        created_ids: List[int] = []
        for spec in candidate_specs:
            prompt = spec.get("prompt") or (current_impl.prompt if current_impl else None)
            model = spec.get("model") or (current_impl.model if current_impl else None)
            max_output_tokens = spec.get("max_output_tokens") or (
                current_impl.max_output_tokens if current_impl else None
            )

            # Required fields guard
            if prompt is None or model is None or max_output_tokens is None:
                continue

            # Compute version as {major}.{latest+1} and increment per created variant
            computed_version = f"{major}.{next_minor}"
            next_minor += 1

            implementation = Implementation(
                task_id=task_id,
                version=computed_version,
                prompt=prompt,
                model=model,
                temperature=spec.get("temperature", current_impl.temperature if current_impl else None),
                reasoning=spec.get("reasoning", current_impl.reasoning if current_impl else None),
                tools=spec.get("tools", current_impl.tools if current_impl else None),
                tool_choice=spec.get("tool_choice", current_impl.tool_choice if current_impl else None),
                max_output_tokens=max_output_tokens,
                temp=spec.get("temp", current_impl.temp if current_impl else False),
            )

            session.add(implementation)
            await session.flush()
            created_ids.append(implementation.id)

        if created_ids:
            await session.commit()

        return created_ids

    async def _evaluate_implementations(
        self,
        session: AsyncSession,
        task_id: int,
        implementation_ids: Sequence[int],
    ) -> Dict[int, Optional[float]]:
        """Evaluate implementations and return mapping impl_id -> final score (or None)."""
        scores: Dict[int, Optional[float]] = {}
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
                .order_by(Evaluation.completed_at.desc().nullslast())
            )
            if not evaluation_row:
                scores[impl_id] = None
                continue

            final_score = await self.evaluation_service.calculate_final_evaluation_score(
                session=session, evaluation=evaluation_row
            )
            scores[impl_id] = final_score

        return scores

    def _select_best(
        self,
        current_best_id: Optional[int],
        current_best_score: Optional[float],
        candidate_scores: Dict[int, Optional[float]],
    ) -> Tuple[Optional[int], Optional[float]]:
        """Choose the best by final score among current best + candidates.

        Contract: tie-breaking strategy to be defined in later milestones.
        """
        # Filter candidates with a numeric score
        scored_candidates: list[tuple[int, float]] = [
            (impl_id, score)
            for impl_id, score in candidate_scores.items()
            if score is not None
        ]

        # If no candidate has a score
        if not scored_candidates:
            # If current has a score, keep it; otherwise, no change
            return current_best_id, current_best_score

        # Find candidate with max score
        best_candidate_id, best_candidate_score = max(
            scored_candidates, key=lambda x: x[1]
        )

        # If current has a score and is greater or equal, keep current (tie/no-op keeps current)
        if current_best_score is not None and current_best_score >= best_candidate_score:
            return current_best_id, current_best_score

        # Otherwise, adopt the better candidate
        return best_candidate_id, best_candidate_score

    def _is_improved(
        self,
        previous_score: Optional[float],
        new_score: Optional[float],
        threshold: float,
    ) -> bool:
        """Check if new_score improves over previous_score by at least threshold."""
        if new_score is None:
            return False
        if previous_score is None:
            return True
        return (new_score - previous_score) >= threshold
