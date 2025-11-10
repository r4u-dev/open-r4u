"""Tests for task grouping queue manager."""

import multiprocessing as mp
import time
from unittest.mock import Mock, patch

import pytest

from app.services.task_grouping_queue import (
    GroupingRequest,
    TaskGroupingQueue,
    get_task_grouping_queue,
)


@pytest.fixture
def queue_manager():
    """Create a fresh queue manager for testing."""
    # Reset singleton
    TaskGroupingQueue._instance = None
    manager = TaskGroupingQueue()
    yield manager
    # Cleanup
    if manager.is_worker_alive():
        manager.stop_worker()
    # Properly close and cleanup any queues
    if manager._queue is not None:
        try:
            manager._queue.close()
            manager._queue.join_thread()
        except Exception:
            pass
        manager._queue = None


def test_singleton_pattern():
    """Test that TaskGroupingQueue follows singleton pattern."""
    TaskGroupingQueue._instance = None
    manager1 = TaskGroupingQueue()
    manager2 = TaskGroupingQueue()
    assert manager1 is manager2


def test_get_task_grouping_queue():
    """Test the module-level getter function."""
    # Reset singleton
    TaskGroupingQueue._instance = None
    manager1 = get_task_grouping_queue()
    manager2 = get_task_grouping_queue()
    assert manager1 is manager2
    assert isinstance(manager1, TaskGroupingQueue)


def test_enqueue_without_worker(queue_manager):
    """Test enqueuing when worker is not started."""
    # Should not raise, but should log error
    queue_manager.enqueue_grouping(
        project_id=1,
        path="/test",
        trace_id=100,
    )
    # Queue should be None
    assert queue_manager._queue is None


def test_enqueue_with_worker(queue_manager):
    """Test enqueuing when worker is running."""
    # Mock the worker process to avoid actually starting it
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    mock_process.pid = 12345

    test_queue = mp.Queue()
    queue_manager._queue = test_queue
    queue_manager._worker_process = mock_process

    try:
        # Enqueue a request
        queue_manager.enqueue_grouping(
            project_id=1,
            path="/api/chat",
            trace_id=100,
        )

        # Should be in queue
        assert queue_manager.get_queue_size() == 1

        # Should be in pending requests
        request = queue_manager.get_pending_request(1, "/api/chat")
        assert request is not None
        assert request.project_id == 1
        assert request.path == "/api/chat"
        assert request.trace_id == 100
    finally:
        queue_manager._queue = None
        queue_manager._worker_process = None
        test_queue.close()
        test_queue.join_thread()


def test_throttling_updates_pending_request(queue_manager):
    """Test that multiple enqueues update the pending request."""
    mock_process = Mock()
    mock_process.is_alive.return_value = True

    test_queue = mp.Queue()
    queue_manager._queue = test_queue
    queue_manager._worker_process = mock_process

    try:
        # Enqueue multiple requests for same project/path
        queue_manager.enqueue_grouping(1, "/test", 100)
        queue_manager.enqueue_grouping(1, "/test", 101)
        queue_manager.enqueue_grouping(1, "/test", 102)

        # Latest request should be in pending
        request = queue_manager.get_pending_request(1, "/test")
        assert request.trace_id == 102

        # All 3 should be in queue though
        assert queue_manager.get_queue_size() == 3
    finally:
        queue_manager._queue = None
        queue_manager._worker_process = None
        test_queue.close()
        test_queue.join_thread()


def test_different_paths_tracked_separately(queue_manager):
    """Test that different paths are tracked separately."""
    mock_process = Mock()
    mock_process.is_alive.return_value = True

    test_queue = mp.Queue()
    queue_manager._queue = test_queue
    queue_manager._worker_process = mock_process

    try:
        # Enqueue for different paths
        queue_manager.enqueue_grouping(1, "/path1", 100)
        queue_manager.enqueue_grouping(1, "/path2", 200)
        queue_manager.enqueue_grouping(2, "/path1", 300)

        # Each should be tracked separately
        assert queue_manager.get_pending_request(1, "/path1").trace_id == 100
        assert queue_manager.get_pending_request(1, "/path2").trace_id == 200
        assert queue_manager.get_pending_request(2, "/path1").trace_id == 300

        # Should have 3 pending keys
        keys = queue_manager.get_pending_keys()
        assert len(keys) == 3
        assert (1, "/path1") in keys
        assert (1, "/path2") in keys
        assert (2, "/path1") in keys
    finally:
        queue_manager._queue = None
        queue_manager._worker_process = None
        test_queue.close()
        test_queue.join_thread()


def test_clear_pending_request(queue_manager):
    """Test clearing a pending request."""
    mock_process = Mock()
    mock_process.is_alive.return_value = True

    test_queue = mp.Queue()
    queue_manager._queue = test_queue
    queue_manager._worker_process = mock_process

    try:
        queue_manager.enqueue_grouping(1, "/test", 100)
        assert queue_manager.get_pending_request(1, "/test") is not None

        queue_manager.clear_pending_request(1, "/test")
        assert queue_manager.get_pending_request(1, "/test") is None
    finally:
        queue_manager._queue = None
        queue_manager._worker_process = None
        test_queue.close()
        test_queue.join_thread()


def test_grouping_request_dataclass():
    """Test GroupingRequest dataclass."""
    request = GroupingRequest(
        project_id=1,
        path="/api/chat",
        trace_id=100,
        timestamp=time.time(),
    )

    assert request.project_id == 1
    assert request.path == "/api/chat"
    assert request.trace_id == 100
    assert isinstance(request.timestamp, float)


def test_worker_alive_status(queue_manager):
    """Test checking if worker is alive."""
    # No worker started
    assert not queue_manager.is_worker_alive()

    # Mock a live worker
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    queue_manager._worker_process = mock_process

    assert queue_manager.is_worker_alive()

    # Mock a dead worker
    mock_process.is_alive.return_value = False
    assert not queue_manager.is_worker_alive()


def test_stop_worker_when_not_started(queue_manager):
    """Test stopping worker when it was never started."""
    # Should not raise
    queue_manager.stop_worker()


def test_stop_worker_when_already_stopped(queue_manager):
    """Test stopping worker that's already stopped."""
    mock_process = Mock()
    mock_process.is_alive.return_value = False
    queue_manager._worker_process = mock_process

    # Should not raise
    queue_manager.stop_worker()


@patch("app.services.task_grouping_queue.mp.Process")
def test_start_worker(mock_process_class, queue_manager):
    """Test starting the worker process."""
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    mock_process.pid = 12345
    mock_process_class.return_value = mock_process

    queue_manager.start_worker()

    # Should create process
    mock_process_class.assert_called_once()

    # Should start it
    mock_process.start.assert_called_once()

    # Should be alive
    assert queue_manager.is_worker_alive()


def test_start_worker_when_already_running(queue_manager):
    """Test starting worker when it's already running."""
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    queue_manager._worker_process = mock_process

    # Should not start another
    queue_manager.start_worker()

    # Should not call start again (was never called the first time in this test)
    mock_process.start.assert_not_called()


def test_get_queue_size_when_no_queue(queue_manager):
    """Test getting queue size when queue doesn't exist."""
    assert queue_manager.get_queue_size() == 0


def test_thread_safety_of_pending_requests(queue_manager):
    """Test that pending requests are thread-safe."""
    import threading

    mock_process = Mock()
    mock_process.is_alive.return_value = True
    test_queue = mp.Queue()
    queue_manager._queue = test_queue
    queue_manager._worker_process = mock_process

    results = []

    def enqueue_many(start_id):
        for i in range(100):
            queue_manager.enqueue_grouping(1, "/test", start_id + i)
            results.append(start_id + i)

    try:
        # Run multiple threads enqueueing
        threads = [
            threading.Thread(target=enqueue_many, args=(i * 100,)) for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have last enqueued value
        request = queue_manager.get_pending_request(1, "/test")
        assert request.trace_id in results

        # All should be in queue
        assert queue_manager.get_queue_size() == 500
    finally:
        # Drain the queue before closing to prevent hanging
        try:
            while not test_queue.empty():
                test_queue.get_nowait()
        except Exception:
            pass
        queue_manager._queue = None
        queue_manager._worker_process = None
        test_queue.close()
        test_queue.join_thread()
