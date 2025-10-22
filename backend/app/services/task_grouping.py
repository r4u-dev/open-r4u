"""Task grouping service for automatically organizing traces into tasks.

This module implements intelligent grouping of traces based on:
1. Path similarity
2. Instructions/system message similarity
3. Template inference to handle parameterized instructions
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import MessageRole
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.services.template_inference import infer_template_from_strings


class TaskGrouper:
    """Groups traces into tasks based on similarity of path and instructions.

    Strategy:
    1. Group traces by path
    2. Within each path group, extract instructions from traces
    3. Compare instructions to find similar patterns
    4. Infer templates for instruction groups
    5. Create tasks with templated instructions
    """

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        min_cluster_size: int = 2,
        max_sample_size: int = 100,
    ):
        """Args:
        similarity_threshold: Minimum similarity score to group traces (0.0-1.0)
        min_cluster_size: Minimum traces needed to create a task
        max_sample_size: Maximum traces to use for template inference

        """
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.max_sample_size = max_sample_size

    async def find_or_create_task_for_trace(
        self, trace_id: int, session: AsyncSession,
    ) -> Task | None:
        """Find an existing task for a trace or create a new one.

        Args:
            trace_id: ID of the trace to group
            session: Database session

        Returns:
            Task if grouped, None if no suitable task found

        """
        # Load the trace with its input items
        query = (
            select(Trace)
            .options(selectinload(Trace.input_items))
            .where(Trace.id == trace_id)
        )
        result = await session.execute(query)
        trace = result.scalar_one_or_none()

        if not trace:
            return None

        # Extract instructions from the trace
        instructions = self._extract_instructions(trace)

        if not instructions:
            return None

        # Try to find matching task by comparing with existing tasks
        matching_task = await self._find_matching_task(trace, instructions, session)

        if matching_task:
            return matching_task

        # Try to create a new task by finding similar traces
        new_task = await self._create_task_from_similar_traces(
            trace, instructions, session,
        )

        return new_task

    async def group_all_traces(self, session: AsyncSession) -> list[Task]:
        """Group all ungrouped traces into tasks.

        Args:
            session: Database session

        Returns:
            List of created tasks

        """
        # Get all traces without a task
        query = (
            select(Trace)
            .options(selectinload(Trace.input_items))
            .where(Trace.task_id.is_(None))
            .order_by(Trace.path, Trace.started_at)
        )
        result = await session.execute(query)
        traces = result.scalars().all()

        if not traces:
            return []

        # Group by path first
        path_groups = defaultdict(list)
        for trace in traces:
            path = trace.path or "default"
            path_groups[path].append(trace)

        created_tasks = []

        # Process each path group
        for path, path_traces in path_groups.items():
            # Group by instructions similarity
            instruction_groups = self._group_by_instructions(path_traces)

            # Create tasks for each group
            for instruction_group in instruction_groups:
                if len(instruction_group) >= self.min_cluster_size:
                    task = await self._create_task_for_group(instruction_group, session)
                    if task:
                        created_tasks.append(task)

        await session.commit()
        return created_tasks

    def _extract_instructions(self, trace: Trace) -> str:
        """Extract instructions from a trace.

        Priority:
        1. trace.instructions field
        2. Concatenate system/developer messages from input

        Args:
            trace: Trace object with input_items loaded

        Returns:
            Extracted instructions string

        """
        # First check if trace has explicit instructions
        if trace.instructions:
            return trace.instructions

        # Otherwise, extract from input items with role=system or developer
        instruction_parts = []

        for input_item in sorted(trace.input_items, key=lambda x: x.position):
            if input_item.type.value == "message":
                role = input_item.data.get("role")
                content = input_item.data.get("content")

                if (
                    role in [MessageRole.SYSTEM.value, MessageRole.DEVELOPER.value]
                    and content
                ):
                    instruction_parts.append(content)

        return "\n".join(instruction_parts) if instruction_parts else ""

    async def _find_matching_task(
        self, trace: Trace, instructions: str, session: AsyncSession,
    ) -> Task | None:
        """Find an existing task that matches the trace's instructions.

        Args:
            trace: The trace to match
            instructions: Extracted instructions from the trace
            session: Database session

        Returns:
            Matching task or None

        """
        # Get all tasks for the same project and path
        query = (
            select(Task)
            .options(selectinload(Task.production_version))
            .where(Task.project_id == trace.project_id)
            .where(Task.production_version_id.isnot(None))
            .join(Implementation, Task.production_version_id == Implementation.id)
            .where(Implementation.model == trace.model)
        )
        result = await session.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return None

        best_task = None
        best_similarity = 0.0

        for task in tasks:
            # Compare instructions using template matching
            if task.production_version.prompt if task.production_version else None:
                similarity = self._compute_instruction_similarity(
                    instructions, task.production_version.prompt if task.production_version else None,
                )

                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_task = task

        return best_task

    async def _create_task_from_similar_traces(
        self, trace: Trace, instructions: str, session: AsyncSession,
    ) -> Task | None:
        """Create a new task by finding similar traces and inferring template.

        Args:
            trace: The seed trace
            instructions: Instructions from the trace
            session: Database session

        Returns:
            Created task or None

        """
        # Find similar traces
        similar_traces = await self._find_similar_traces(trace, instructions, session)

        if len(similar_traces) < self.min_cluster_size:
            return None

        # Create task from group
        task = await self._create_task_for_group(similar_traces, session)
        return task

    async def _find_similar_traces(
        self, seed_trace: Trace, seed_instructions: str, session: AsyncSession,
    ) -> list[Trace]:
        """Find traces similar to the seed trace.

        Args:
            seed_trace: The trace to compare against
            seed_instructions: Instructions from the seed trace
            session: Database session

        Returns:
            List of similar traces (including seed)

        """
        # Get traces with same path and model, without a task
        query = (
            select(Trace)
            .options(selectinload(Trace.input_items))
            .where(Trace.project_id == seed_trace.project_id)
            .where(Trace.model == seed_trace.model)
            .where(Trace.path == seed_trace.path)
            .where(Trace.task_id.is_(None))
        )
        result = await session.execute(query)
        candidate_traces = result.scalars().all()

        similar_traces = [seed_trace]

        for trace in candidate_traces:
            if trace.id == seed_trace.id:
                continue

            trace_instructions = self._extract_instructions(trace)
            if not trace_instructions:
                continue

            similarity = self._compute_instruction_similarity(
                seed_instructions, trace_instructions,
            )

            if similarity >= self.similarity_threshold:
                similar_traces.append(trace)

        return similar_traces

    def _group_by_instructions(self, traces: list[Trace]) -> list[list[Trace]]:
        """Group traces by instruction similarity.

        Args:
            traces: List of traces to group

        Returns:
            List of trace groups

        """
        if not traces:
            return []

        groups = []
        remaining = list(traces)

        while remaining:
            # Pick a seed trace
            seed = remaining.pop(0)
            seed_instructions = self._extract_instructions(seed)

            if not seed_instructions:
                continue

            # Find similar traces
            group = [seed]
            to_remove = []

            for trace in remaining:
                trace_instructions = self._extract_instructions(trace)
                if not trace_instructions:
                    continue

                similarity = self._compute_instruction_similarity(
                    seed_instructions, trace_instructions,
                )

                if similarity >= self.similarity_threshold:
                    group.append(trace)
                    to_remove.append(trace)

            # Remove grouped traces from remaining
            for trace in to_remove:
                remaining.remove(trace)

            if len(group) >= self.min_cluster_size:
                groups.append(group)

        return groups

    def _compute_instruction_similarity(self, instr1: str, instr2: str) -> float:
        """Compute similarity between two instruction strings.

        Uses token-based Jaccard similarity with length penalty.

        Args:
            instr1: First instruction string
            instr2: Second instruction string

        Returns:
            Similarity score (0.0-1.0)

        """
        # Tokenize and normalize
        tokens1 = set(self._tokenize(instr1.lower()))
        tokens2 = set(self._tokenize(instr2.lower()))

        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        jaccard = intersection / union if union > 0 else 0.0

        # Length similarity (penalize very different lengths)
        len1, len2 = len(instr1), len(instr2)
        length_sim = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0

        # Combined score (70% Jaccard, 30% length)
        return 0.7 * jaccard + 0.3 * length_sim

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words (alphanumeric sequences)."""
        tokens = []
        i = 0
        while i < len(text):
            if text[i].isalnum():
                j = i
                while j < len(text) and text[j].isalnum():
                    j += 1
                tokens.append(text[i:j])
                i = j
            else:
                i += 1
        return tokens

    async def _create_task_for_group(
        self, traces: list[Trace], session: AsyncSession,
    ) -> Task | None:
        """Create a task from a group of similar traces.

        Args:
            traces: Group of similar traces
            session: Database session

        Returns:
            Created task

        """
        if not traces:
            return None

        # Use the first trace as reference
        reference_trace = traces[0]

        # Extract instructions from all traces
        instruction_strings = []
        for trace in traces:
            instructions = self._extract_instructions(trace)
            if instructions:
                instruction_strings.append(instructions)

        # Sample if too many
        if len(instruction_strings) > self.max_sample_size:
            step = len(instruction_strings) // self.max_sample_size
            instruction_strings = instruction_strings[::step][: self.max_sample_size]

        # Infer template from instructions
        if len(instruction_strings) >= 2:
            templated_instructions = infer_template_from_strings(instruction_strings)
        else:
            templated_instructions = (
                instruction_strings[0]
                if instruction_strings
                else reference_trace.prompt or ""
            )

        # Determine common prompt template
        prompt_strings = [t.prompt for t in traces if t.prompt]
        if len(prompt_strings) >= 2:
            templated_prompt = infer_template_from_strings(
                prompt_strings[: self.max_sample_size],
            )
        else:
            templated_prompt = prompt_strings[0] if prompt_strings else ""

        # Use templated_instructions as the main prompt if available, otherwise use templated_prompt
        final_prompt = (
            templated_instructions if templated_instructions else templated_prompt
        )

        # Create the task first
        task = Task(
            project_id=reference_trace.project_id,
            path=reference_trace.path,
        )

        session.add(task)
        await session.flush()

        # Create the implementation
        implementation = Implementation(
            task_id=task.id,
            prompt=final_prompt,
            model=reference_trace.model,
            tools=reference_trace.tools,
            response_schema=reference_trace.response_schema,
            temperature=reference_trace.temperature,
            tool_choice=reference_trace.tool_choice,
            reasoning=reference_trace.reasoning,
            max_output_tokens=reference_trace.total_tokens
            or 4096,  # Use a default if not available
        )

        session.add(implementation)
        await session.flush()

        # Set as production version
        task.production_version_id = implementation.id

        # Assign traces to the task
        for trace in traces:
            trace.task_id = task.id

        return task


async def find_or_create_task_for_trace(
    trace_id: int, session: AsyncSession, similarity_threshold: float = 0.6,
) -> Task | None:
    """Convenience function to find or create a task for a trace.

    Args:
        trace_id: ID of the trace
        session: Database session
        similarity_threshold: Minimum similarity for grouping

    Returns:
        Task if found/created, None otherwise

    """
    grouper = TaskGrouper(similarity_threshold=similarity_threshold)
    return await grouper.find_or_create_task_for_trace(trace_id, session)


async def group_all_traces(
    session: AsyncSession, similarity_threshold: float = 0.6, min_cluster_size: int = 2,
) -> list[Task]:
    """Convenience function to group all ungrouped traces.

    Args:
        session: Database session
        similarity_threshold: Minimum similarity for grouping
        min_cluster_size: Minimum traces to create a task

    Returns:
        List of created tasks

    """
    grouper = TaskGrouper(
        similarity_threshold=similarity_threshold, min_cluster_size=min_cluster_size,
    )
    return await grouper.group_all_traces(session)


async def try_match_existing_task(
    trace_id: int, session: AsyncSession, similarity_threshold: float = 0.6,
) -> Task | None:
    """Fast matching: Try to match a trace to an existing task without creating new ones.

    This is used for auto-grouping on trace creation - it's fast because it only
    queries existing tasks and doesn't analyze other traces or create new tasks.

    Args:
        trace_id: ID of the trace to match
        session: Database session
        similarity_threshold: Minimum similarity to match tasks

    Returns:
        Task if matched, None if no suitable task found

    """
    # Load trace with input items for instruction extraction
    query = (
        select(Trace)
        .options(selectinload(Trace.input_items))
        .where(Trace.id == trace_id)
    )
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        return None

    # Extract instructions
    grouper = TaskGrouper(similarity_threshold=similarity_threshold)
    instructions = grouper._extract_instructions(trace)

    if not instructions:
        return None

    # Try to find matching task (fast - only queries existing tasks)
    return await grouper._find_matching_task(trace, instructions, session)
