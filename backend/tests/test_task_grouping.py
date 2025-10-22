"""Tests for task grouping service."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import ItemType
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace, TraceInputItem
from app.services.task_grouping import (
    TaskGrouper,
)


@pytest.mark.asyncio
async def test_extract_instructions_from_explicit_field(test_session: AsyncSession):
    """Test extracting instructions from trace.instructions field."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        instructions="You are a helpful assistant.",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0),
    )
    test_session.add(trace)
    await test_session.commit()

    grouper = TaskGrouper()
    extracted = grouper._extract_instructions(trace)

    assert extracted == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_extract_instructions_from_system_message(test_session: AsyncSession):
    """Test extracting instructions from system messages in input."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0),
    )
    test_session.add(trace)
    await test_session.flush()

    # Add system message
    input_item = TraceInputItem(
        trace_id=trace.id,
        type=ItemType.MESSAGE,
        data={"role": "system", "content": "You are a weather assistant."},
        position=0,
    )
    test_session.add(input_item)
    await test_session.commit()

    # Reload trace with input items
    query = (
        select(Trace)
        .where(Trace.id == trace.id)
        .options(selectinload(Trace.input_items))
    )
    result = await test_session.execute(query)
    trace = result.scalar_one()

    grouper = TaskGrouper()
    extracted = grouper._extract_instructions(trace)

    assert extracted == "You are a weather assistant."


@pytest.mark.asyncio
async def test_compute_instruction_similarity():
    """Test instruction similarity computation."""
    grouper = TaskGrouper()

    # Identical instructions
    instr1 = "You are a helpful assistant."
    instr2 = "You are a helpful assistant."
    similarity = grouper._compute_instruction_similarity(instr1, instr2)
    assert similarity == 1.0

    # Similar instructions
    instr3 = "You are a weather assistant."
    instr4 = "You are a helpful weather assistant."
    similarity = grouper._compute_instruction_similarity(instr3, instr4)
    assert similarity > 0.6

    # Different instructions
    instr5 = "You are a helpful assistant."
    instr6 = "Calculate the fibonacci sequence."
    similarity = grouper._compute_instruction_similarity(instr5, instr6)
    assert similarity < 0.5


@pytest.mark.asyncio
async def test_group_traces_by_path(test_session: AsyncSession):
    """Test grouping traces by path and instructions."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create traces with same path and similar instructions
    traces = []
    for i, name in enumerate(["John", "Mary", "Alice"]):
        trace = Trace(
            project_id=project.id,
            model="gpt-4",
            path="/api/greet",
            instructions=f"Greet user {name} politely.",
            prompt=f"Say hello to {name}",
            result=f"Hello {name}!",
            started_at=datetime(2025, 10, 17, 10, 0, 0),
        )
        test_session.add(trace)
        traces.append(trace)

    await test_session.commit()

    # Group traces
    grouper = TaskGrouper(min_cluster_size=2)
    created_tasks = await grouper.group_all_traces(test_session)

    assert len(created_tasks) == 1
    task = created_tasks[0]

    # Check that task has templated instructions in production version
    await test_session.refresh(task, ["production_version"])
    assert (
        task.production_version
        and task.production_version.prompt
        and "{var_" in task.production_version.prompt
    )

    # Check that all traces are assigned to the task
    for trace in traces:
        await test_session.refresh(trace)
        assert trace.task_id == task.id


@pytest.mark.asyncio
async def test_find_matching_task(test_session):
    """Test finding matching tasks based on similarity."""
    # Create a project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create a task with templated instructions
    task = Task(
        project_id=project.id,
        path="/greet",
    )
    test_session.add(task)
    await test_session.flush()

    # Create implementation with templated prompt
    implementation = Implementation(
        task_id=task.id,
        prompt="Greet user {var_0} politely.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    await test_session.commit()

    # Create a trace with similar instructions
    trace = Trace(
        project_id=project.id,
        path="/greet",
        model="gpt-4",
        instructions="Greet user Bob politely.",
        started_at=datetime(2025, 10, 17, 10, 0, 0),
    )
    test_session.add(trace)
    await test_session.commit()

    # Create task grouper and find matching task
    grouper = TaskGrouper()

    # Extract instructions from trace
    result = await test_session.execute(
        select(Trace)
        .where(Trace.id == trace.id)
        .options(selectinload(Trace.input_items)),
    )
    trace_with_input = result.scalar_one()
    instructions = grouper._extract_instructions(trace_with_input)

    matched_task = await grouper._find_matching_task(trace, instructions, test_session)

    # Should find the existing task
    assert matched_task is not None
    assert matched_task.id == task.id


@pytest.mark.asyncio
async def test_api_group_single_trace(client: AsyncClient, test_session: AsyncSession):
    """Test the API endpoint to group a single trace."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create similar traces
    traces = []
    for i, name in enumerate(["Alice", "Bob", "Charlie"]):
        trace = Trace(
            project_id=project.id,
            model="gpt-4",
            path="/api/greet",
            instructions=f"Say hello to {name}",
            result=f"Hello {name}!",
            started_at=datetime(2025, 10, 17, 10, 0, 0),
        )
        test_session.add(trace)
        traces.append(trace)

    await test_session.commit()

    # Group the first trace
    response = await client.post(f"/traces/{traces[0].id}/group")
    assert response.status_code == 200
    data = response.json()

    # Should have created a task and assigned it
    assert data["task_id"] is not None

    # Verify task was created
    await test_session.refresh(traces[0])
    assert traces[0].task_id is not None


@pytest.mark.asyncio
async def test_api_group_all_traces(client: AsyncClient, test_session: AsyncSession):
    """Test the API endpoint to group all traces."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create traces in two groups
    # Group 1: Greetings
    for name in ["Alice", "Bob", "Charlie"]:
        trace = Trace(
            project_id=project.id,
            model="gpt-4",
            path="/api/greet",
            instructions=f"Say hello to {name}",
            result=f"Hello {name}!",
            started_at=datetime(2025, 10, 17, 10, 0, 0),
        )
        test_session.add(trace)

    # Group 2: Weather
    for location in ["London", "Paris", "Tokyo"]:
        trace = Trace(
            project_id=project.id,
            model="gpt-4",
            path="/api/weather",
            instructions=f"Get weather for {location}",
            result=f"Weather in {location}: Sunny",
            started_at=datetime(2025, 10, 17, 10, 0, 0),
        )
        test_session.add(trace)

    await test_session.commit()

    # Group all traces
    response = await client.post("/tasks/group-traces?min_cluster_size=2")
    assert response.status_code == 201
    data = response.json()

    # Should have created 2 tasks (one per path group)
    assert len(data) >= 2

    # Check that tasks have production versions with templated prompts
    from sqlalchemy.orm import selectinload

    for task_data in data:
        task_query = (
            select(Task)
            .where(Task.id == task_data["id"])
            .options(selectinload(Task.production_version))
        )
        result = await test_session.execute(task_query)
        task = result.scalar_one()
        assert task.production_version is not None
        assert "{var_" in task.production_version.prompt


@pytest.mark.asyncio
async def test_group_traces_with_developer_role(test_session: AsyncSession):
    """Test extracting instructions from developer role messages."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0),
    )
    test_session.add(trace)
    await test_session.flush()

    # Add developer message
    input_item = TraceInputItem(
        trace_id=trace.id,
        type=ItemType.MESSAGE,
        data={"role": "developer", "content": "You are a coding assistant."},
        position=0,
    )
    test_session.add(input_item)
    await test_session.commit()

    # Reload trace with input items
    query = (
        select(Trace)
        .where(Trace.id == trace.id)
        .options(selectinload(Trace.input_items))
    )
    result = await test_session.execute(query)
    trace = result.scalar_one()

    grouper = TaskGrouper()
    extracted = grouper._extract_instructions(trace)

    assert extracted == "You are a coding assistant."


@pytest.mark.asyncio
async def test_group_traces_min_cluster_size(test_session: AsyncSession):
    """Test that traces below min_cluster_size don't create tasks."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create only 1 trace (below min_cluster_size of 2)
    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        instructions="Single trace",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0),
    )
    test_session.add(trace)
    await test_session.commit()

    # Try to group
    grouper = TaskGrouper(min_cluster_size=2)
    created_tasks = await grouper.group_all_traces(test_session)

    # Should not create any tasks
    assert len(created_tasks) == 0

    # Trace should not be assigned to a task
    await test_session.refresh(trace)
    assert trace.task_id is None
