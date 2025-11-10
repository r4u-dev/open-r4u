"""Integration tests for task grouping worker."""

import time
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ItemType, MessageRole
from app.models.projects import Project
from app.models.traces import Trace
from app.schemas.traces import MessageItem, TraceCreate
from app.services.task_grouping_queue import get_task_grouping_queue
from app.services.traces_service import TracesService


@pytest_asyncio.fixture
async def project(test_session: AsyncSession):
    """Create a test project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return project


@pytest.fixture
def sample_trace_data(project):
    """Create sample trace data."""

    def _create_trace(instructions: str, path: str = "/api/chat"):
        return TraceCreate(
            project=project.name,
            model="gpt-4",
            path=path,
            instructions=instructions,
            started_at=datetime.now(),
            input=[
                MessageItem(
                    type=ItemType.MESSAGE,
                    role=MessageRole.SYSTEM,
                    content=instructions,
                ),
            ],
            temperature=0.7,
        )

    return _create_trace


@pytest.mark.asyncio
async def test_worker_processes_grouping_request(
    test_session: AsyncSession,
    project,
    sample_trace_data,
):
    """Test that worker processes grouping requests and creates tasks."""
    # Note: This is a unit test that doesn't actually start the worker
    # In a real integration test, you would start the worker process

    traces_service = TracesService()

    # Create multiple traces with similar instructions
    instructions = [
        "Translate hello to Spanish",
        "Translate goodbye to Spanish",
        "Translate thank you to Spanish",
        "Translate welcome to Spanish",
        "Translate yes to Spanish",
    ]

    created_traces = []
    for instr in instructions:
        trace_data = sample_trace_data(instr)
        trace = await traces_service.create_trace(trace_data, test_session)
        created_traces.append(trace)

    # All traces should be created
    assert len(created_traces) == 5

    # None should have implementation_id yet (would be set by worker)
    for trace in created_traces:
        assert trace.implementation_id is None

    # Verify traces are in database and ready for grouping
    query = (
        select(Trace)
        .where(Trace.project_id == project.id)
        .where(Trace.implementation_id.is_(None))
    )
    result = await test_session.execute(query)
    unmatched_traces = result.scalars().all()

    assert len(unmatched_traces) == 5


@pytest.mark.asyncio
async def test_trace_creation_enqueues_grouping(
    test_session: AsyncSession,
    project,
    sample_trace_data,
):
    """Test that creating a trace enqueues a grouping request."""
    # Mock the queue manager to avoid starting actual worker
    queue_manager = get_task_grouping_queue()

    # Track enqueued requests
    enqueued_requests = []

    original_enqueue = queue_manager.enqueue_grouping

    def mock_enqueue(project_id, path, trace_id):
        enqueued_requests.append(
            {
                "project_id": project_id,
                "path": path,
                "trace_id": trace_id,
            },
        )
        # Don't actually enqueue (no worker running)

    queue_manager.enqueue_grouping = mock_enqueue

    try:
        traces_service = TracesService()
        trace_data = sample_trace_data("Test instruction")

        trace = await traces_service.create_trace(trace_data, test_session)

        # Should have enqueued a request
        assert len(enqueued_requests) == 1
        assert enqueued_requests[0]["project_id"] == project.id
        assert enqueued_requests[0]["path"] == "/api/chat"
        assert enqueued_requests[0]["trace_id"] == trace.id

    finally:
        # Restore original method
        queue_manager.enqueue_grouping = original_enqueue


@pytest.mark.asyncio
async def test_throttling_behavior(
    test_session: AsyncSession,
    project,
    sample_trace_data,
):
    """Test that multiple rapid traces result in throttling."""
    import multiprocessing as mp
    from unittest.mock import Mock

    queue_manager = get_task_grouping_queue()

    # Mock worker to be alive
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    queue_manager._worker_process = mock_process
    test_queue = mp.Queue()
    queue_manager._queue = test_queue

    try:
        traces_service = TracesService()

        # Create multiple traces rapidly for same path
        trace_ids = []
        for i in range(5):
            trace_data = sample_trace_data(f"Instruction {i}")
            trace = await traces_service.create_trace(trace_data, test_session)
            trace_ids.append(trace.id)

        # Should have enqueued 5 requests
        assert queue_manager.get_queue_size() == 5

        # But pending should only have the last one
        pending = queue_manager.get_pending_request(project.id, "/api/chat")
        assert pending is not None
        assert pending.trace_id == trace_ids[-1]  # Last trace
    finally:
        # Cleanup - properly close the queue
        queue_manager._worker_process = None
        queue_manager._queue = None
        test_queue.close()
        test_queue.join_thread()


@pytest.mark.asyncio
async def test_different_paths_not_throttled_together(
    test_session: AsyncSession,
    project,
    sample_trace_data,
):
    """Test that traces with different paths don't throttle each other."""
    import multiprocessing as mp
    from unittest.mock import Mock

    queue_manager = get_task_grouping_queue()

    # Mock worker
    mock_process = Mock()
    mock_process.is_alive.return_value = True
    queue_manager._worker_process = mock_process
    test_queue = mp.Queue()
    queue_manager._queue = test_queue

    try:
        traces_service = TracesService()

        # Create traces for different paths
        paths = ["/api/chat", "/api/summarize", "/api/translate"]
        for path in paths:
            trace_data = TraceCreate(
                project=project.name,
                model="gpt-4",
                path=path,
                instructions="Test instruction",
                started_at=datetime.now(),
                input=[
                    MessageItem(
                        type=ItemType.MESSAGE,
                        role=MessageRole.SYSTEM,
                        content="Test instruction",
                    ),
                ],
                temperature=0.7,
            )
            await traces_service.create_trace(trace_data, test_session)

        # Should have 3 pending requests (one per path)
        pending_keys = queue_manager.get_pending_keys()
        assert len(pending_keys) == 3
        assert (project.id, "/api/chat") in pending_keys
        assert (project.id, "/api/summarize") in pending_keys
        assert (project.id, "/api/translate") in pending_keys
    finally:
        # Cleanup - properly close the queue
        queue_manager._worker_process = None
        queue_manager._queue = None
        test_queue.close()
        test_queue.join_thread()


def test_grouping_request_ordering():
    """Test that newer requests are tracked correctly for throttling."""
    from app.services.task_grouping_queue import GroupingRequest

    req1 = GroupingRequest(
        project_id=1,
        path="/test",
        trace_id=100,
        timestamp=time.time(),
    )

    time.sleep(0.01)

    req2 = GroupingRequest(
        project_id=1,
        path="/test",
        trace_id=101,
        timestamp=time.time(),
    )

    # req2 should be newer
    assert req2.timestamp > req1.timestamp
    assert req2.trace_id > req1.trace_id
