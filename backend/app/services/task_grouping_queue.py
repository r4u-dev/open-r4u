"""Queue manager for background task grouping operations."""

import logging
import multiprocessing as mp
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GroupingRequest:
    """Request to perform task grouping."""

    project_id: int
    path: str
    trace_id: int
    timestamp: float


class TaskGroupingQueue:
    """Manages queue for background task grouping operations.

    This is a singleton that maintains a multiprocessing queue for sending
    grouping requests to a background worker process. It tracks pending
    requests to enable throttling.

    Thread-safe for use in FastAPI's async environment.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize queue manager."""
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._queue: mp.Queue | None = None
        self._worker_process: mp.Process | None = None
        self._pending_requests: dict[tuple[int, str], GroupingRequest] = {}
        self._pending_lock = threading.Lock()
        self._shutdown_event: mp.Event | None = None

    def start_worker(self) -> None:
        """Start the background worker process."""
        if self._worker_process is not None and self._worker_process.is_alive():
            logger.warning("Worker process already running")
            return

        # Create queue and shutdown event
        self._queue = mp.Queue(maxsize=1000)
        self._shutdown_event = mp.Event()

        # Import here to avoid circular imports
        from app.workers.task_grouping_worker import run_worker

        # Start worker process
        self._worker_process = mp.Process(
            target=run_worker,
            args=(self._queue, self._shutdown_event),
            daemon=True,
            name="TaskGroupingWorker",
        )
        self._worker_process.start()
        logger.info(f"Started task grouping worker (PID: {self._worker_process.pid})")

    def stop_worker(self, timeout: float = 5.0) -> None:
        """Stop the background worker process gracefully.

        Args:
            timeout: Maximum time to wait for worker to stop (seconds)

        """
        if self._worker_process is None:
            logger.warning("No worker process to stop")
            return

        if not self._worker_process.is_alive():
            logger.warning("Worker process already stopped")
            return

        logger.info("Stopping task grouping worker...")

        # Signal shutdown
        if self._shutdown_event:
            self._shutdown_event.set()

        # Send sentinel value to unblock queue.get()
        try:
            if self._queue:
                self._queue.put(None, timeout=1.0)
        except Exception as e:
            logger.warning(f"Failed to send shutdown signal to queue: {e}")

        # Wait for process to terminate
        self._worker_process.join(timeout=timeout)

        if self._worker_process.is_alive():
            logger.warning("Worker did not stop gracefully, terminating...")
            self._worker_process.terminate()
            self._worker_process.join(timeout=2.0)

            if self._worker_process.is_alive():
                logger.error("Worker did not terminate, killing...")
                self._worker_process.kill()
                self._worker_process.join()

        logger.info("Task grouping worker stopped")
        self._worker_process = None

    def enqueue_grouping(
        self,
        project_id: int,
        path: str | None,
        trace_id: int,
    ) -> None:
        """Enqueue a task grouping request.

        This tracks the latest request for each (project_id, path) combination
        to enable throttling. Multiple rapid requests for the same path will
        result in only the latest being processed.

        Args:
            project_id: Project ID for the trace
            path: Trace path (e.g., "/api/chat")
            trace_id: ID of the trace that triggered grouping

        """
        if self._queue is None:
            logger.error("Queue not initialized, cannot enqueue grouping request")
            return

        if not self._worker_process or not self._worker_process.is_alive():
            logger.error("Worker process not running, cannot enqueue grouping request")
            return

        request = GroupingRequest(
            project_id=project_id,
            path=path,
            trace_id=trace_id,
            timestamp=time.time(),
        )

        # Update pending requests (for throttling)
        key = (project_id, path)
        with self._pending_lock:
            self._pending_requests[key] = request

        # Add to queue
        try:
            self._queue.put(request, timeout=1.0)
            logger.info(
                f"Enqueued grouping request for trace {trace_id} "
                f"(project={project_id}, path={path})",
            )
        except Exception as e:
            logger.error(f"Failed to enqueue grouping request: {e}")

    def get_pending_request(
        self,
        project_id: int,
        path: str,
    ) -> GroupingRequest | None:
        """Get the latest pending request for a (project_id, path) combination.

        This is used by the worker to check if a newer request exists before
        processing, enabling throttling.

        Args:
            project_id: Project ID
            path: Trace path

        Returns:
            Latest pending request, or None if no pending request

        """
        key = (project_id, path)
        with self._pending_lock:
            return self._pending_requests.get(key)

    def clear_pending_request(self, project_id: int, path: str) -> None:
        """Clear pending request after processing.

        Args:
            project_id: Project ID
            path: Trace path

        """
        key = (project_id, path)
        with self._pending_lock:
            self._pending_requests.pop(key, None)

    def get_queue_size(self) -> int:
        """Get approximate size of the queue.

        Returns:
            Number of pending requests in queue

        """
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def get_pending_keys(self) -> list[tuple[int, str]]:
        """Get list of all pending (project_id, path) keys.

        Returns:
            List of (project_id, path) tuples with pending requests

        """
        with self._pending_lock:
            return list(self._pending_requests.keys())

    def is_worker_alive(self) -> bool:
        """Check if worker process is alive.

        Returns:
            True if worker is running, False otherwise

        """
        return self._worker_process is not None and self._worker_process.is_alive()


# Singleton instance
_queue_manager: TaskGroupingQueue | None = None
_manager_lock = threading.Lock()


def get_task_grouping_queue() -> TaskGroupingQueue:
    """Get or create the singleton task grouping queue manager.

    Returns:
        TaskGroupingQueue instance

    """
    global _queue_manager
    if _queue_manager is None:
        with _manager_lock:
            if _queue_manager is None:
                _queue_manager = TaskGroupingQueue()
    return _queue_manager
