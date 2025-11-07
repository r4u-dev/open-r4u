"""Task grouping service for automatically organizing traces into tasks.

This module implements intelligent grouping of traces based on:
1. Path similarity
2. Instructions/system message similarity
3. Template inference to handle parameterized instructions
"""

import re
from collections import defaultdict

from datasketch import MinHash, MinHashLSH
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.services.implementation_matcher import ImplementationMatcher
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
    ):
        """Initialize task grouper.

        Args:
            session: Database session
            min_cluster_size: Minimum traces needed to create a group
            similarity_threshold: Similarity score threshold (0-1) to group traces

        """
        self.session = session
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
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
        instructions = self.extract_instructions(trace)

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

    def extract_instructions(self, trace: Trace) -> str:
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

            trace_instructions = self.extract_instructions(trace)
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
        """Group traces by instruction similarity using MinHash-based clusterization.

        Uses ngram-based MinHash with LSH for efficient similarity search, filtering
        to shared ngrams across the corpus to improve clustering quality.

        Args:
            traces: List of traces to group

        Returns:
            List of trace groups (clusters)

        """
        # Extract instructions from all traces
        texts, trace_indices = self._extract_instruction_texts(traces)

        if not texts:
            return []

        # If only one text, return single group
        if len(texts) == 1:
            return [[traces[trace_indices[0]]]]

        # Compute shared ngrams across corpus
        shared_ngrams = self._compute_shared_ngrams(texts)

        # If no shared ngrams found, cannot produce meaningful clusters
        # Empty shared_ngrams would cause empty MinHashes with similarity 1.0
        if not shared_ngrams:
            return []

        # Calculate MinHashes using only shared ngrams
        minhashes = [
            self._get_minhash(text, allowed_ngrams=shared_ngrams) for text in texts
        ]

        # Build clusters using LSH
        return self._build_clusters_with_lsh(
            minhashes,
            traces,
            trace_indices,
        )

    def _extract_instruction_texts(
        self,
        traces: list[Trace],
    ) -> tuple[list[str], list[int]]:
        """Extract instruction texts from traces.

        Args:
            traces: List of traces

        Returns:
            Tuple of (texts list, trace_indices list)

        """
        texts = []
        trace_indices = []

        for i, trace in enumerate(traces):
            instructions = self.extract_instructions(trace)
            if instructions:
                texts.append(instructions)
                trace_indices.append(i)

        return texts, trace_indices

    def _compute_shared_ngrams(self, texts: list[str]) -> set[str]:
        """Compute shared ngrams across corpus.

        Args:
            texts: List of instruction texts

        Returns:
            Set of shared ngrams

        """
        # Compute corpus-wide ngram frequencies
        ngram_text_count = defaultdict(int)

        for text in texts:
            tokens = self._tokenize_preserve_case(text)
            text_ngrams = self._generate_ngrams(tokens, n=3)

            # Count that this ngram appears in this text
            for gram in text_ngrams:
                ngram_text_count[gram] += 1

        min_ngram_count = 2
        return {
            gram for gram, count in ngram_text_count.items() if count >= min_ngram_count
        }

    def _build_clusters_with_lsh(
        self,
        minhashes: list[MinHash],
        traces: list[Trace],
        trace_indices: list[int],
    ) -> list[list[Trace]]:
        """Build clusters using MinHashLSH.

        Args:
            minhashes: List of MinHash objects
            traces: Original list of traces
            trace_indices: Indices mapping minhashes to traces

        Returns:
            List of trace clusters

        """
        # Use LSH for efficient similarity search
        lsh = MinHashLSH(
            threshold=self.similarity_threshold,
            num_perm=128,
        )

        for i, mh in enumerate(minhashes):
            lsh.insert(f"t{i}", mh)

        # Build clusters
        clusters = []
        visited = set()

        for i, mh in enumerate(minhashes):
            if i in visited:
                continue

            # Find near-duplicates using LSH
            similar = lsh.query(mh)
            indices = [int(s[1:]) for s in similar]

            # Filter by actual Jaccard similarity to remove false positives
            filtered_indices = self._filter_similar_indices(
                i,
                indices,
                mh,
                minhashes,
                visited,
            )

            # Create trace group from filtered indices
            trace_group = [traces[trace_indices[idx]] for idx in filtered_indices]
            clusters.append(trace_group)
            visited.update(filtered_indices)

        return clusters

    def _filter_similar_indices(
        self,
        seed_idx: int,
        candidate_indices: list[int],
        seed_minhash: MinHash,
        minhashes: list[MinHash],
        visited: set[int],
    ) -> list[int]:
        """Filter candidate indices by actual Jaccard similarity.

        Args:
            seed_idx: Index of seed item
            candidate_indices: Candidate indices from LSH query
            seed_minhash: MinHash of seed item
            minhashes: List of all MinHash objects
            visited: Set of already visited indices

        Returns:
            List of filtered indices including seed

        """
        filtered_indices = [seed_idx]  # Always include self

        for idx in candidate_indices:
            if idx != seed_idx and idx not in visited:
                actual_sim = seed_minhash.jaccard(minhashes[idx])
                if actual_sim >= self.similarity_threshold:
                    filtered_indices.append(idx)

        return filtered_indices

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
        """Tokenize text into words (lowercase).

        Args:
            text: Text to tokenize

        Returns:
            List of lowercase tokens

        """
        # Simple word tokenization (lowercase for backward compatibility)
        return [token.lower() for token in re.findall(r"\w+", text)]

    def _tokenize_preserve_case(self, text: str) -> list[str]:
        """Tokenize text, preserving casing.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens (words and punctuation)

        """
        # Tokenize preserving casing, including punctuation
        return re.findall(r"\w+|[^\w\s]", text)

    def _generate_ngrams(
        self,
        tokens: list[str],
        n: int = 3,
    ) -> set[str]:
        """Generate ngrams from tokens.

        Args:
            tokens: List of tokens
            n: Ngram size (default 3)

        Returns:
            Set of ngram strings

        """
        # Generate all ngrams
        all_grams = [
            " ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)
        ]
        return set(all_grams)

    def _get_minhash(
        self,
        text: str,
        num_perm: int = 128,
        allowed_ngrams: set[str] | None = None,
    ) -> MinHash:
        """Create MinHash from text, optionally filtering to allowed ngrams.

        Args:
            text: Text to create MinHash for
            num_perm: Number of permutations for MinHash
            allowed_ngrams: Optional set of ngrams to filter to (corpus-wide filtering)

        Returns:
            MinHash object

        """
        tokens = self._tokenize_preserve_case(text)
        grams = self._generate_ngrams(tokens, n=3)

        # Filter to allowed ngrams if provided (corpus-wide filtering)
        if allowed_ngrams is not None:
            grams = grams & allowed_ngrams

        m = MinHash(num_perm=num_perm)
        for g in grams:
            m.update(g.encode("utf8"))
        return m

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
            instructions = self.extract_instructions(trace)
            if instructions:
                instruction_strings.append(instructions)

        if not instruction_strings:
            return None

        # Infer template from instruction strings
        template = infer_template_from_strings(instruction_strings)

        # Get project name
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
        matcher = ImplementationMatcher()

        for trace in traces:
            instructions = self.extract_instructions(trace)
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
) -> Task | None:
    """Find or create task for a trace.

    Args:
        trace_id: Trace ID
        session: Database session
        min_cluster_size: Minimum traces for grouping
        similarity_threshold: Similarity threshold for grouping

    Returns:
        Task if found/created, None otherwise

    """
    grouper = TaskGrouper(session, min_cluster_size, similarity_threshold)
    return await grouper.find_or_create_task_for_trace(trace_id)


async def group_all_traces(
    project_id: int,
    session: AsyncSession,
    model: str | None = None,
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.6,
) -> list[Task]:
    """Group all traces in a project.

    Args:
        project_id: Project ID
        session: Database session
        model: Optional model filter
        min_cluster_size: Minimum traces for grouping
        similarity_threshold: Similarity threshold for grouping

    Returns:
        List of created tasks

    """
    grouper = TaskGrouper(session, min_cluster_size, similarity_threshold)
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
    instructions = grouper.extract_instructions(trace)

    if not instructions:
        return None

    # Try to match
    return await grouper._find_matching_task(trace, instructions)
