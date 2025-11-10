"""Background worker for processing task grouping requests."""

import asyncio
import logging
import multiprocessing as mp
import sys
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models.traces import Trace
from app.schemas.tasks import ImplementationCreate, TaskCreate
from app.services.task_grouping import TemplateFinder
from app.services.task_grouping_queue import GroupingRequest
from app.services.task_service import TaskService

# Configure logging for worker process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class TaskGroupingWorker:
    """Worker that processes task grouping requests in background."""

    def __init__(self, queue: mp.Queue, shutdown_event: mp.Event):
        """Initialize worker.

        Args:
            queue: Queue to receive grouping requests
            shutdown_event: Event to signal shutdown

        """
        self.queue = queue
        self.shutdown_event = shutdown_event
        self.settings = get_settings()

        # Create database engine for this process
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Track which requests we've seen to enable throttling
        self._pending_requests: dict[tuple[int, str], GroupingRequest] = {}

    async def run(self) -> None:
        """Main worker loop."""
        logger.info("Task grouping worker started")

        try:
            while not self.shutdown_event.is_set():
                try:
                    # Get next request (blocking with timeout)
                    request = self.queue.get(timeout=1.0)

                    # Check for shutdown sentinel
                    if request is None:
                        logger.info("Received shutdown signal")
                        break

                    # Process request
                    await self._process_request(request)

                except mp.queues.Empty:
                    # Timeout, check shutdown event and continue
                    continue
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}", exc_info=True)
                    # Continue processing despite errors

        finally:
            logger.info("Shutting down worker...")
            await self.engine.dispose()
            logger.info("Worker shut down complete")

    async def _process_request(self, request: GroupingRequest) -> None:
        """Process a single grouping request.

        Args:
            request: Grouping request to process

        """
        key = (request.project_id, request.path)

        # Update tracking
        if key in self._pending_requests:
            existing = self._pending_requests[key]
            if existing.trace_id > request.trace_id:
                logger.info(
                    f"Skipping grouping for trace {request.trace_id} "
                    f"(newer trace {existing.trace_id} pending for same path)",
                )
                return

        self._pending_requests[key] = request

        # Check if this is the latest request
        latest = self._pending_requests.get(key)
        if latest and latest.trace_id != request.trace_id:
            logger.info(
                f"Skipping grouping for trace {request.trace_id} "
                f"(trace {latest.trace_id} is newer)",
            )
            return

        # Process the grouping
        try:
            logger.info(
                f"Processing grouping for trace {request.trace_id} "
                f"(project={request.project_id}, path={request.path})",
            )

            start_time = time.time()
            async with self.SessionLocal() as session:
                result = await self._perform_grouping(
                    request.project_id,
                    request.path,
                    session,
                )

            elapsed = time.time() - start_time

            if result:
                logger.info(
                    f"Completed grouping for trace {request.trace_id}: "
                    f"created {result['tasks_created']} tasks with "
                    f"{result['traces_grouped']} traces in {elapsed:.2f}s",
                )
            else:
                logger.info(
                    f"No grouping performed for trace {request.trace_id} "
                    f"(insufficient traces) in {elapsed:.2f}s",
                )

            # Clear from pending after successful processing
            if self._pending_requests.get(key) == request:
                del self._pending_requests[key]

        except Exception as e:
            logger.error(
                f"Failed to process grouping for trace {request.trace_id}: {e}",
                exc_info=True,
            )

    async def _perform_grouping(
        self,
        project_id: int,
        path: str,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """Perform task grouping for a specific project and path.

        This is the core grouping logic, extracted from TracesService.

        Args:
            project_id: Project ID
            path: Trace path
            session: Database session

        Returns:
            Dict with results (tasks_created, traces_grouped) or None if no grouping

        """
        # Find all unmatched traces for this project and path
        traces_query = (
            select(Trace)
            .where(Trace.project_id == project_id)
            .where(Trace.path == path)
            .where(Trace.implementation_id.is_(None))
            .options(joinedload(Trace.input_items))
            .options(joinedload(Trace.project))
        )
        result = await session.execute(traces_query)
        unmatched_traces = result.unique().scalars().all()

        if len(unmatched_traces) < self.settings.min_cluster_size:
            logger.debug(
                f"Only {len(unmatched_traces)} unmatched traces with path '{path}', "
                f"need {self.settings.min_cluster_size} to create implementation",
            )
            return None

        # Extract prompts from traces
        prompts = []
        trace_map = {}  # Map index to trace

        for trace in unmatched_traces:
            trace_input_items = [
                {"type": item.type.value, **item.data} for item in trace.input_items
            ]
            prompt = await self._extract_system_prompt_from_trace(trace_input_items)
            if prompt:
                prompts.append(prompt)
                trace_map[len(prompts) - 1] = trace

        if len(prompts) < self.settings.min_matching_traces:
            logger.debug(
                f"Only {len(prompts)} traces with valid prompts, "
                f"need {self.settings.min_matching_traces} to create implementation",
            )
            return None

        logger.info(
            f"Found {len(prompts)} unmatched traces with prompts, "
            f"attempting to create task/implementation groups",
        )

        # Use TemplateFinder to group similar prompts
        template_finder = TemplateFinder(
            self.settings.min_segment_words,
            self.settings.min_matching_traces,
        )

        # Group prompts into templates
        groups = template_finder.group_strings(prompts)

        if not groups:
            logger.debug(f"Could not create any groups for path '{path}'")
            return None

        # Create task and implementation for each group
        task_service = TaskService(session)
        tasks_created = 0
        traces_grouped = 0

        for template, prompt_indices in groups.items():
            # Get sample trace for model and settings
            sample_idx = prompt_indices[0]
            sample_trace = trace_map[sample_idx]

            # Create implementation data
            impl_data = ImplementationCreate(
                prompt=template,
                model=sample_trace.model,
                max_output_tokens=1000,  # Default
                temperature=sample_trace.temperature,
                tools=sample_trace.tools,
                tool_choice=sample_trace.tool_choice,
                reasoning=sample_trace.reasoning,
                temp=True,  # Mark as temporary/auto-generated
            )

            # Create task data - name and description will be auto-generated
            task_data = TaskCreate(
                project=sample_trace.project.name
                if sample_trace.project
                else "Default Project",
                name=None,  # Will be auto-generated
                description=None,  # Will be auto-generated
                implementation=impl_data,
            )

            # Create task with auto-generated name and description
            task = await task_service.create_task(task_data)

            # Get the implementation ID from production_version_id
            if not task.production_version_id:
                logger.warning(
                    f"Failed to create implementation for task {task.id}, skipping",
                )
                continue

            impl_id = task.production_version_id

            # Assign traces to this implementation and extract variables
            group_traces = 0
            for idx in prompt_indices:
                if idx in trace_map:
                    trace = trace_map[idx]
                    match, variables = template_finder.match_template(
                        template,
                        prompts[idx],
                    )
                    if match:
                        trace.implementation_id = impl_id
                        trace.prompt_variables = variables
                        group_traces += 1

            logger.info(
                f"Created task {task.id} with implementation {impl_id} "
                f"for {group_traces} traces with template: {template[:100]}...",
            )

            tasks_created += 1
            traces_grouped += group_traces

        # Commit all changes
        await session.commit()

        return {
            "tasks_created": tasks_created,
            "traces_grouped": traces_grouped,
        }

    async def _extract_system_prompt_from_trace(
        self,
        input_items: list[dict[str, Any]],
    ) -> str | None:
        """Extract system prompt from trace input items.

        Args:
            input_items: List of input item dicts

        Returns:
            System prompt text or None if not found

        """
        for item in input_items:
            if item.get("type") == "text" and item.get("role") == "system":
                return item.get("text")
            if item.get("type") == "message":
                # Handle message type with role and content
                if item.get("role") == "system":
                    content = item.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        # Handle content array (e.g., [{"type": "text", "text": "..."}])
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                return part.get("text")

        # If no system message, try first user message
        for item in input_items:
            if item.get("type") == "text" and item.get("role") == "user":
                return item.get("text")
            if item.get("type") == "message" and item.get("role") == "user":
                content = item.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            return part.get("text")

        return None


def run_worker(queue: mp.Queue, shutdown_event: mp.Event) -> None:
    """Entry point for worker process.

    Args:
        queue: Queue to receive grouping requests
        shutdown_event: Event to signal shutdown

    """
    try:
        worker = TaskGroupingWorker(queue, shutdown_event)
        asyncio.run(worker.run())
    except Exception as e:
        logger.error(f"Worker process crashed: {e}", exc_info=True)
        sys.exit(1)
