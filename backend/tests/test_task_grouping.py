"""Tests for implementation matching (formerly task grouping).

These tests verify that traces are automatically matched to implementations
based on prompt templates with placeholder extraction.
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import ItemType
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace, TraceInputItem
from app.services.implementation_matcher import (
    ImplementationMatcher,
    extract_system_prompt_from_trace,
)


@pytest_asyncio.fixture
async def project(test_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()
    return project


@pytest_asyncio.fixture
async def task(test_session: AsyncSession, project: Project) -> Task:
    """Create a test task."""
    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()
    return task


@pytest.mark.asyncio
async def test_extract_system_prompt_from_input_items(test_session: AsyncSession):
    """Test extracting system prompt from trace input items."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0, tzinfo=UTC),
    )
    test_session.add(trace)
    await test_session.flush()

    # Add system message
    input_item = TraceInputItem(
        trace_id=trace.id,
        type=ItemType.MESSAGE,
        data={"role": "system", "content": "You are a helpful assistant."},
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

    # Extract from input items
    input_items = [{"type": item.type.value, **item.data} for item in trace.input_items]
    extracted = extract_system_prompt_from_trace(input_items)

    assert extracted == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_trace_auto_matches_to_implementation(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test that a trace automatically matches an implementation."""
    # Create an implementation with a template
    impl = Implementation(
        task_id=task.id,
        prompt="Greet user {name} politely.",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    # Create a trace via API (triggers auto-matching)
    payload = {
        "model": "gpt-4",
        "input": [
            {
                "type": "message",
                "role": "system",
                "content": "Greet user Alice politely.",
            },
            {"type": "message", "role": "user", "content": "Hello!"},
        ],
        "result": "Hello Alice!",
        "started_at": "2025-10-17T10:00:00Z",
        "completed_at": "2025-10-17T10:00:01Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] == impl.id
    assert data["prompt_variables"] == {"name": "Alice"}


@pytest.mark.asyncio
async def test_multiple_traces_match_same_implementation(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test that multiple traces match the same implementation with different variables."""
    # Create an implementation
    impl = Implementation(
        task_id=task.id,
        prompt="Say hello to {name} from {location}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    # Create multiple traces with different values
    test_cases = [
        ("Alice", "London", {"name": "Alice", "location": "London"}),
        ("Bob", "Paris", {"name": "Bob", "location": "Paris"}),
        ("Charlie", "Tokyo", {"name": "Charlie", "location": "Tokyo"}),
    ]

    for name, location, expected_vars in test_cases:
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": f"Say hello to {name} from {location}",
                },
            ],
            "result": f"Hello {name}!",
            "started_at": "2025-10-17T10:00:00Z",
            "completed_at": "2025-10-17T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] == impl.id
        assert data["prompt_variables"] == expected_vars


@pytest.mark.asyncio
async def test_traces_with_different_paths_match_different_implementations(
    test_session: AsyncSession,
    client: AsyncClient,
    project: Project,
):
    """Test that traces with different contexts match different implementations."""
    # Create task and implementations for different purposes
    task1 = Task(project_id=project.id, path="/api/greet")
    task2 = Task(project_id=project.id, path="/api/weather")
    test_session.add_all([task1, task2])
    await test_session.flush()

    impl1 = Implementation(
        task_id=task1.id,
        prompt="Greet user {name}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task2.id,
        prompt="Get weather for {city}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    # Create greeting trace
    payload1 = {
        "model": "gpt-4",
        "input": [
            {"type": "message", "role": "system", "content": "Greet user Alice"},
        ],
        "result": "Hello Alice!",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
        "path": "/api/greet",
    }
    response1 = await client.post("/traces", json=payload1)
    assert response1.status_code == 201
    assert response1.json()["implementation_id"] == impl1.id

    # Create weather trace
    payload2 = {
        "model": "gpt-4",
        "input": [
            {"type": "message", "role": "system", "content": "Get weather for London"},
        ],
        "result": "Sunny",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
        "path": "/api/weather",
    }
    response2 = await client.post("/traces", json=payload2)
    assert response2.status_code == 201
    assert response2.json()["implementation_id"] == impl2.id


@pytest.mark.asyncio
async def test_placeholder_extraction_with_special_characters(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test placeholder extraction with special characters like emails and numbers."""
    impl = Implementation(
        task_id=task.id,
        prompt="User {email} from account {account_id}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    payload = {
        "model": "gpt-4",
        "input": [
            {
                "type": "message",
                "role": "system",
                "content": "User john.doe@example.com from account 12345",
            },
        ],
        "result": "Processed",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] == impl.id
    assert data["prompt_variables"] == {
        "email": "john.doe@example.com",
        "account_id": "12345",
    }


@pytest.mark.asyncio
async def test_no_match_when_structure_differs(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test that traces don't match when the structure is completely different."""
    impl = Implementation(
        task_id=task.id,
        prompt="Greet user {name}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    # Create a trace with completely different structure
    payload = {
        "model": "gpt-4",
        "input": [
            {
                "type": "message",
                "role": "system",
                "content": "Calculate the fibonacci sequence",
            },
        ],
        "result": "1, 1, 2, 3, 5, 8",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] is None
    assert data["prompt_variables"] is None


@pytest.mark.asyncio
async def test_template_matching_is_case_sensitive():
    """Test that template matching is case sensitive."""
    matcher = ImplementationMatcher()

    template = "Hello {name}"
    prompt1 = "Hello World"
    prompt2 = "hello World"

    result1 = matcher.match_template(template, prompt1)
    result2 = matcher.match_template(template, prompt2)

    assert result1 is not None
    assert result1["variables"] == {"name": "World"}
    assert result2 is None  # Case mismatch


@pytest.mark.asyncio
async def test_multiline_template_matching(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test matching with multiline templates."""
    impl = Implementation(
        task_id=task.id,
        prompt="""You are {role}.
User: {name}
Task: {task}""",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    payload = {
        "model": "gpt-4",
        "input": [
            {
                "type": "message",
                "role": "system",
                "content": """You are a developer.
User: Alice
Task: Review code""",
            },
        ],
        "result": "OK",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] == impl.id
    assert data["prompt_variables"] == {
        "role": "a developer",
        "name": "Alice",
        "task": "Review code",
    }


@pytest.mark.asyncio
async def test_first_implementation_wins_when_multiple_match(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test that when multiple implementations match, the first one is used."""
    # Create two implementations with same template
    impl1 = Implementation(
        task_id=task.id,
        prompt="Hello {name}",
        model="gpt-4",
        max_output_tokens=1000,
        version="1.0",
    )
    test_session.add(impl1)
    await test_session.flush()

    impl2 = Implementation(
        task_id=task.id,
        prompt="Hello {name}",
        model="gpt-4",
        max_output_tokens=2000,
        version="2.0",
    )
    test_session.add(impl2)
    await test_session.commit()

    payload = {
        "model": "gpt-4",
        "input": [
            {"type": "message", "role": "system", "content": "Hello Alice"},
        ],
        "result": "Hi!",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    # Should match the first implementation (by ID)
    assert data["implementation_id"] == impl1.id


@pytest.mark.asyncio
async def test_model_must_match_for_implementation_matching(
    test_session: AsyncSession,
    client: AsyncClient,
    task: Task,
):
    """Test that model name must match for implementation matching."""
    impl = Implementation(
        task_id=task.id,
        prompt="Hello {name}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl)
    await test_session.commit()

    # Create trace with different model
    payload = {
        "model": "gpt-3.5-turbo",  # Different model
        "input": [
            {"type": "message", "role": "system", "content": "Hello Alice"},
        ],
        "result": "Hi!",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Test Project",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["implementation_id"] is None


@pytest.mark.asyncio
async def test_project_isolation_in_matching(
    test_session: AsyncSession,
    client: AsyncClient,
):
    """Test that implementations from different projects don't match."""
    # Create two projects with similar implementations
    project1 = Project(name="Project 1")
    project2 = Project(name="Project 2")
    test_session.add_all([project1, project2])
    await test_session.flush()

    task1 = Task(project_id=project1.id)
    task2 = Task(project_id=project2.id)
    test_session.add_all([task1, task2])
    await test_session.flush()

    impl1 = Implementation(
        task_id=task1.id,
        prompt="Hello {name}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task2.id,
        prompt="Hello {name}",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    # Create trace in project 1
    payload = {
        "model": "gpt-4",
        "input": [
            {"type": "message", "role": "system", "content": "Hello Alice"},
        ],
        "result": "Hi!",
        "started_at": "2025-10-17T10:00:00Z",
        "project": "Project 1",
    }

    response = await client.post("/traces", json=payload)
    assert response.status_code == 201

    data = response.json()
    # Should match impl1 from project 1, not impl2 from project 2
    assert data["implementation_id"] == impl1.id


@pytest.mark.asyncio
async def test_api_group_endpoint_is_disabled(
    client: AsyncClient,
    test_session: AsyncSession,
    project: Project,
):
    """Test that the old /traces/{id}/group endpoint is disabled/no-op."""
    trace = Trace(
        project_id=project.id,
        model="gpt-4",
        instructions="Test",
        result="Response",
        started_at=datetime(2025, 10, 17, 10, 0, 0, tzinfo=UTC),
    )
    test_session.add(trace)
    await test_session.commit()

    # The endpoint should still exist but not do anything
    response = await client.post(f"/traces/{trace.id}/group")
    assert response.status_code == 200

    # Trace should not have implementation_id set by this endpoint
    data = response.json()
    # The endpoint returns the trace but doesn't modify it
    assert data["id"] == trace.id
