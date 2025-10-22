"""Tests for automatic task matching on trace creation."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_auto_match_trace_to_existing_task(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that a new trace automatically matches an existing task."""
    # Create a project
    project = Project(name="Auto Match Test")
    test_session.add(project)
    await test_session.flush()

    # Create task and implementation
    task = Task(
        project_id=project.id,
        path="/greet",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="You are a helpful assistant.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    test_session.add(task)
    await test_session.commit()

    # Create a trace via API (should auto-match to the task)
    response = await client.post(
        "/traces",
        json={
            "project": "Auto Match Test",
            "model": "gpt-4",
            "path": "/greet",
            "instructions": "Say hello to Alice",
            "started_at": "2025-10-17T10:00:00Z",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 201
    trace_data = response.json()

    # Verify trace was auto-matched to the task
    assert trace_data["task_id"] == task.id


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_no_auto_match_when_no_similar_task(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that trace is not matched when no similar task exists."""
    # Create a project
    project = Project(name="No Match Test")
    test_session.add(project)
    await test_session.flush()

    # Create task and implementation with different instructions
    task = Task(
        project_id=project.id,
        path="/weather",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="You are a weather assistant.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    test_session.add(task)
    await test_session.commit()

    # Create a trace with different instructions (should NOT match)
    response = await client.post(
        "/traces",
        json={
            "project": "No Match Test",
            "model": "gpt-4",
            "path": "/greet",  # Different path
            "instructions": "Say hello to Alice",
            "started_at": "2025-10-17T10:00:00Z",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 201
    trace_data = response.json()

    # Verify trace was NOT matched (no similar task exists)
    assert trace_data["task_id"] is None


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_auto_match_respects_similarity_threshold(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that auto-matching respects similarity threshold."""
    # Create a project
    project = Project(name="Similarity Test")
    test_session.add(project)
    await test_session.flush()

    # Create task and implementation with specific instructions
    task = Task(
        project_id=project.id,
        path="/api",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="You are a helpful assistant.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    test_session.add(task)
    await test_session.commit()

    # Create a trace with VERY different instructions (should NOT match)
    response = await client.post(
        "/traces",
        json={
            "project": "Similarity Test",
            "model": "gpt-4",
            "path": "/api",
            "instructions": "Tell me a joke about cats",  # Completely different
            "started_at": "2025-10-17T10:00:00Z",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 201
    trace_data = response.json()

    # Verify trace was NOT matched (similarity too low)
    assert trace_data["task_id"] is None


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_auto_match_with_system_message_instructions(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test auto-matching when instructions come from system messages."""
    # Create a project
    project = Project(name="System Message Test")
    test_session.add(project)
    await test_session.flush()

    # Create task and implementation with templated instructions
    task = Task(
        project_id=project.id,
        path="/chat",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="You are a helpful assistant.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    test_session.add(task)
    await test_session.commit()

    # Create a trace with instructions in system message (should auto-match)
    response = await client.post(
        "/traces",
        json={
            "project": "System Message Test",
            "model": "gpt-4",
            "path": "/chat",
            "started_at": "2025-10-17T10:00:00Z",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "Help the user with Python questions",
                },
                {"type": "message", "role": "user", "content": "What is a list?"},
            ],
        },
    )

    assert response.status_code == 201
    trace_data = response.json()

    # Verify trace was auto-matched to the task
    assert trace_data["task_id"] == task.id


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_batch_grouping_creates_tasks_for_ungrouped_traces(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that batch grouping creates tasks for ungrouped traces."""
    # Create a project
    project = Project(name="Batch Test")
    test_session.add(project)
    await test_session.flush()

    # Create multiple similar traces (no existing tasks to match)
    for name in ["Alice", "Bob", "Charlie"]:
        response = await client.post(
            "/traces",
            json={
                "project": "Batch Test",
                "model": "gpt-4",
                "path": "/greet",
                "instructions": f"Say hello to {name}",
                "started_at": "2025-10-17T10:00:00Z",
                "input": [
                    {"type": "message", "role": "user", "content": f"Hello {name}"},
                ],
            },
        )
        assert response.status_code == 201
        # All traces should be ungrouped initially
        assert response.json()["task_id"] is None

    # Run batch grouping
    response = await client.post("/tasks/group-traces?min_cluster_size=2")
    assert response.status_code == 201
    tasks_data = response.json()

    # Should have created 1 task
    assert len(tasks_data) >= 1
    task = tasks_data[0]
    assert task["path"] == "/greet"

    # Verify traces are now assigned to the task
    query = select(Trace).where(Trace.project_id == project.id)
    result = await test_session.execute(query)
    traces = result.scalars().all()

    for trace in traces:
        assert trace.task_id is not None


@pytest.mark.skip(
    reason="Auto-grouping feature not yet integrated into trace creation API",
)
@pytest.mark.asyncio
async def test_subsequent_traces_auto_match_after_batch_grouping(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that after batch grouping, new traces auto-match to created tasks."""
    # Create a project
    project = Project(name="Sequential Test")
    test_session.add(project)
    await test_session.flush()

    # Create initial traces
    for name in ["Alice", "Bob"]:
        await client.post(
            "/traces",
            json={
                "project": "Sequential Test",
                "model": "gpt-4",
                "path": "/greet",
                "instructions": f"Say hello to {name}",
                "started_at": "2025-10-17T10:00:00Z",
                "input": [
                    {"type": "message", "role": "user", "content": f"Hello {name}"},
                ],
            },
        )

    # Run batch grouping to create task
    response = await client.post("/tasks/group-traces?min_cluster_size=2")
    assert response.status_code == 201
    tasks = response.json()
    assert len(tasks) >= 1
    created_task_id = tasks[0]["id"]

    # Create a new similar trace (should auto-match to the created task)
    response = await client.post(
        "/traces",
        json={
            "project": "Sequential Test",
            "model": "gpt-4",
            "path": "/greet",
            "instructions": "Say hello to Charlie",
            "started_at": "2025-10-17T10:00:00Z",
            "input": [{"type": "message", "role": "user", "content": "Hello Charlie"}],
        },
    )

    assert response.status_code == 201
    trace_data = response.json()

    # Verify new trace auto-matched to the created task
    assert trace_data["task_id"] == created_task_id
