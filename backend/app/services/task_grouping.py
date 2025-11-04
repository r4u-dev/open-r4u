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

from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.services.task_service import TaskService
from app.services.template_inference import infer_template_from_strings


class TaskGrouper:
    """Groups traces into tasks based on similarity of path and instructions.

    Strategy:
    1. Group traces by path
    2. Within each path group, extract instructions from traces
    3. Compare instructions to find similar patterns
    4. For similar traces, infer a common template
    5. Create Task + Implementation(s) for each distinct template
    """

    def __init__(
        self,
        session: AsyncSession,
        min_cluster_size: int = 3,
        similarity_threshold: float = 0.6,
        min_consecutive_words: int = 3,
    ):
        """Initialize task grouper.

        Args:
            session: Database session
            min_cluster_size: Minimum traces needed to create a group
            similarity_threshold: Similarity score threshold (0-1) to group traces
            min_consecutive_words: Minimum number of consecutive words required for template detection (default: 3)

        """
        self.session = session
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self.min_consecutive_words = min_consecutive_words
        self.task_service = TaskService(session)

    async def find_or_create_task_for_trace(
        self,
        trace_id: int,
    ) -> Task | None:
        """Find or create a task for a single trace.

        This looks for similar traces and tries to create a task if enough
        similar traces exist.

        Args:
            trace_id: ID of the trace to process

        Returns:
            Task if found or created, None otherwise

        """
        # Load trace with input items
        query = (
            select(Trace)
            .where(Trace.id == trace_id)
            .options(selectinload(Trace.input_items))
        )
        result = await self.session.execute(query)
        trace = result.scalar_one_or_none()

        if not trace:
            return None

        # Extract instructions from the trace
        instructions = self._extract_instructions(trace)

        if not instructions:
            return None

        # Find existing task that matches
        task = await self._find_matching_task(trace, instructions)
        if task:
            return task

        # Try to create new task from similar traces
        return await self._create_task_from_similar_traces(trace, instructions)

    async def group_all_traces(
        self,
        project_id: int,
        model: str | None = None,
    ) -> list[Task]:
        """Group all ungrouped traces in a project into tasks.

        Args:
            project_id: Project ID to group traces for
            model: Optional model filter

        Returns:
            List of created tasks

        """
        # Get all traces without implementation
        query = (
            select(Trace)
            .where(Trace.project_id == project_id)
            .where(Trace.implementation_id.is_(None))
            .options(selectinload(Trace.input_items))
        )

        result = await self.session.execute(query)
        traces = result.scalars().all()

        if len(traces) < self.min_cluster_size:
            return []

        # Group by path first
        path_groups = defaultdict(list)
        for trace in traces:
            path_groups[trace.path].append(trace)

        # Process each path group
        created_tasks = []
        for path, path_traces in path_groups.items():
            if len(path_traces) < self.min_cluster_size:
                continue

            # Group by instruction similarity
            instruction_groups = self._group_by_instructions(path_traces)

            # Create task for each group
            for group in instruction_groups:
                if len(group) >= self.min_cluster_size:
                    task = await self._create_task_for_group(group)
                    if task:
                        created_tasks.append(task)

        return created_tasks

    def _extract_instructions(self, trace: Trace) -> str:
        """Extract instructions from a trace.

        Priority:
        1. trace.instructions field
        2. First message from input (regardless of role)

        Args:
            trace: Trace object with input_items loaded

        Returns:
            Extracted instructions string

        """
        # First check if trace has explicit instructions
        if trace.instructions:
            return trace.instructions

        # Otherwise, extract the first message from input items
        for input_item in sorted(trace.input_items, key=lambda x: x.position):
            if input_item.type.value == "message":
                content = input_item.data.get("content")
                if content:
                    return content

        return ""

    async def _find_matching_task(
        self,
        trace: Trace,
        instructions: str,
    ) -> Task | None:
        """Find an existing task that matches this trace's instructions.

        Args:
            trace: Trace to match
            instructions: Extracted instructions

        Returns:
            Matching task or None

        """
        # Get all implementations for this project and model
        query = (
            select(Implementation)
            .join(Task, Implementation.task_id == Task.id)
            .where(Task.project_id == trace.project_id)
            .where(Implementation.model == trace.model)
            .options(selectinload(Implementation.task))
        )

        result = await self.session.execute(query)
        implementations = result.scalars().all()

        # Try to match instructions against each implementation's prompt
        from app.services.implementation_matcher import ImplementationMatcher

        matcher = ImplementationMatcher()

        for impl in implementations:
            match_result = matcher.match_template(impl.prompt, instructions)

            if match_result and match_result["match"]:
                # Assign trace to this implementation
                trace.implementation_id = impl.id
                trace.prompt_variables = match_result["variables"]
                await self.session.flush()

                return impl.task

        return None

    async def _create_task_from_similar_traces(
        self,
        trace: Trace,
        instructions: str,
    ) -> Task | None:
        """Create a task from similar traces.

        Args:
            trace: Seed trace
            instructions: Instructions from seed trace

        Returns:
            Created task or None

        """
        # Find similar traces
        similar_traces = await self._find_similar_traces(trace, instructions)

        if len(similar_traces) < self.min_cluster_size:
            return None

        # Create task and implementation
        return await self._create_task_for_group(similar_traces)

    async def _find_similar_traces(
        self,
        seed_trace: Trace,
        seed_instructions: str,
    ) -> list[Trace]:
        """Find traces similar to the seed trace.

        Args:
            seed_trace: Reference trace
            seed_instructions: Instructions from seed trace

        Returns:
            List of similar traces (including seed)

        """
        # Query traces with same project, model, path, and no implementation
        query = (
            select(Trace)
            .where(Trace.project_id == seed_trace.project_id)
            .where(Trace.model == seed_trace.model)
            .where(Trace.implementation_id.is_(None))
            .options(selectinload(Trace.input_items))
        )

        # Handle path comparison (including null paths)
        if seed_trace.path is not None:
            query = query.where(Trace.path == seed_trace.path)
        else:
            query = query.where(Trace.path.is_(None))

        result = await self.session.execute(query)
        candidates = result.scalars().all()

        # Filter by instruction similarity
        similar = [seed_trace]

        for trace in candidates:
            if trace.id == seed_trace.id:
                continue

            trace_instructions = self._extract_instructions(trace)
            if not trace_instructions:
                continue

            similarity = self._compute_instruction_similarity(
                seed_instructions,
                trace_instructions,
            )

            if similarity >= self.similarity_threshold:
                similar.append(trace)

        return similar

    def _group_by_instructions(self, traces: list[Trace]) -> list[list[Trace]]:
        """Group traces by instruction similarity.

        Args:
            traces: List of traces to group

        Returns:
            List of trace groups

        """
        groups = []
        remaining = list(traces)

        while remaining:
            # Pick first remaining trace as seed
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
                    seed_instructions,
                    trace_instructions,
                )

                if similarity >= self.similarity_threshold:
                    group.append(trace)
                    to_remove.append(trace)

            # Remove grouped traces from remaining
            for trace in to_remove:
                remaining.remove(trace)

            groups.append(group)

        return groups

    def _compute_instruction_similarity(
        self,
        instructions1: str,
        instructions2: str,
    ) -> float:
        """Compute similarity between two instruction strings.

        Uses Jaccard similarity on tokenized instructions.

        Args:
            instructions1: First instruction string
            instructions2: Second instruction string

        Returns:
            Similarity score (0-1)

        """
        tokens1 = set(self._tokenize(instructions1))
        tokens2 = set(self._tokenize(instructions2))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words.

        Args:
            text: Text to tokenize

        Returns:
            List of lowercase tokens

        """
        import re

        # Simple word tokenization
        return [token.lower() for token in re.findall(r"\w+", text)]

    async def _create_task_for_group(
        self,
        traces: list[Trace],
    ) -> Task | None:
        """Create a task and implementation for a group of similar traces.

        Args:
            traces: Group of similar traces

        Returns:
            Created task or None

        """
        if not traces:
            return None

        # Use first trace for metadata
        first_trace = traces[0]

        # Collect instruction strings for template inference
        instruction_strings = []
        for trace in traces:
            instructions = self._extract_instructions(trace)
            if instructions:
                instruction_strings.append(instructions)

        if not instruction_strings:
            return None

        # Infer template from instruction strings
        template = infer_template_from_strings(
            instruction_strings,
            min_consecutive_words=self.min_consecutive_words,
        )

        # Get project name
        from app.models.projects import Project

        project_query = select(Project).where(Project.id == first_trace.project_id)
        project_result = await self.session.execute(project_query)
        project = project_result.scalar_one()

        # Create implementation data
        implementation_data = ImplementationCreate(
            version="0.1",
            prompt=template,
            model=first_trace.model,
            temperature=first_trace.temperature,
            tool_choice=first_trace.tool_choice,
            tools=None,  # tools would need to be converted to schema format
            reasoning=None,  # reasoning would need to be converted to schema format
            max_output_tokens=first_trace.total_tokens or 4096,
        )

        # Create task data
        task_data = TaskCreate(
            project=project.name,
            path=first_trace.path,
            response_schema=first_trace.response_schema,
            implementation=implementation_data,
        )

        # Create task and implementation using task service
        task = await self.task_service.create_task(task_data)

        # Get the created implementation
        implementation = await self.session.get(
            Implementation,
            task.production_version_id,
        )

        # Match traces to this implementation
        from app.services.implementation_matcher import ImplementationMatcher

        matcher = ImplementationMatcher()

        for trace in traces:
            instructions = self._extract_instructions(trace)
            if not instructions:
                continue

            match_result = matcher.match_template(template, instructions)

            if match_result and match_result["match"]:
                trace.implementation_id = implementation.id
                trace.prompt_variables = match_result["variables"]

        await self.session.flush()

        return task


async def find_or_create_task_for_trace(
    trace_id: int,
    session: AsyncSession,
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.6,
    min_consecutive_words: int = 3,
) -> Task | None:
    """Convenience function to find or create task for a trace.

    Args:
        trace_id: Trace ID
        session: Database session
        min_cluster_size: Minimum traces for grouping
        similarity_threshold: Similarity threshold for grouping
        min_consecutive_words: Minimum consecutive words for template detection

    Returns:
        Task if found/created, None otherwise

    """
    grouper = TaskGrouper(
        session,
        min_cluster_size,
        similarity_threshold,
        min_consecutive_words,
    )
    return await grouper.find_or_create_task_for_trace(trace_id)


async def group_all_traces(
    project_id: int,
    session: AsyncSession,
    model: str | None = None,
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.6,
    min_consecutive_words: int = 3,
) -> list[Task]:
    """Convenience function to group all traces in a project.

    Args:
        project_id: Project ID
        session: Database session
        model: Optional model filter
        min_cluster_size: Minimum traces for grouping
        similarity_threshold: Similarity threshold for grouping
        min_consecutive_words: Minimum consecutive words for template detection

    Returns:
        List of created tasks

    """
    grouper = TaskGrouper(
        session,
        min_cluster_size,
        similarity_threshold,
        min_consecutive_words,
    )
    return await grouper.group_all_traces(project_id, model)


async def try_match_existing_task(
    trace_id: int,
    session: AsyncSession,
    similarity_threshold: float = 0.6,
) -> Task | None:
    """Try to match trace to existing task without creating new ones.

    Args:
        trace_id: Trace ID
        session: Database session
        similarity_threshold: Similarity threshold

    Returns:
        Matched task or None

    """
    # Load trace
    query = (
        select(Trace)
        .where(Trace.id == trace_id)
        .options(selectinload(Trace.input_items))
    )
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        return None

    # Extract instructions
    grouper = TaskGrouper(session, similarity_threshold=similarity_threshold)
    instructions = grouper._extract_instructions(trace)

    if not instructions:
        return None

    # Try to match
    return await grouper._find_matching_task(trace, instructions)
