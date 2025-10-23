"""Integration tests for automatic trace-to-implementation matching."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace


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


class TestTraceImplementationMatching:
    """Test automatic matching of traces to implementations."""

    @pytest.mark.asyncio
    async def test_trace_matches_exact_implementation(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that a trace automatically matches an implementation with exact prompt."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] == impl.id
        assert data["prompt_variables"] == {}

        # Verify in database
        result = await test_session.execute(select(Trace).where(Trace.id == data["id"]))
        trace = result.scalar_one()
        assert trace.implementation_id == impl.id
        assert trace.prompt_variables == {}

    @pytest.mark.asyncio
    async def test_trace_matches_implementation_with_placeholders(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that a trace matches implementation and extracts placeholder values."""
        # Create an implementation with placeholders
        impl = Implementation(
            task_id=task.id,
            prompt="Hello, {name}! You are user #{user_id}. Your role is {role}.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace with actual values
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "Hello, Alice! You are user #42. Your role is admin.",
                },
                {"type": "message", "role": "user", "content": "What can I do?"},
            ],
            "result": "You have full access.",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] == impl.id
        assert data["prompt_variables"] == {
            "name": "Alice",
            "user_id": "42",
            "role": "admin",
        }

        # Verify in database
        result = await test_session.execute(select(Trace).where(Trace.id == data["id"]))
        trace = result.scalar_one()
        assert trace.implementation_id == impl.id
        assert trace.prompt_variables == {
            "name": "Alice",
            "user_id": "42",
            "role": "admin",
        }

    @pytest.mark.asyncio
    async def test_trace_no_match_different_model(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that trace doesn't match implementation with different model."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace with different model
        payload = {
            "model": "gpt-3.5-turbo",  # Different model
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] is None
        assert data["prompt_variables"] is None

    @pytest.mark.asyncio
    async def test_trace_no_match_different_prompt(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that trace doesn't match when prompt structure is different."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace with different prompt
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a mean robot.",  # Different prompt
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Go away!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] is None
        assert data["prompt_variables"] is None

    @pytest.mark.asyncio
    async def test_trace_with_explicit_implementation_id(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that explicit implementation_id is not overridden by auto-matching."""
        # Create two implementations
        impl1 = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl1)
        await test_session.flush()

        impl2 = Implementation(
            task_id=task.id,
            prompt="You are a different assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl2)
        await test_session.commit()

        # Create a trace with explicit implementation_id
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
            "implementation_id": impl2.id,  # Explicitly set
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        # Should keep the explicit implementation_id, not auto-match
        assert data["implementation_id"] == impl2.id

    @pytest.mark.asyncio
    async def test_trace_matches_first_implementation_when_multiple_match(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that when multiple implementations match, the first one is used."""
        # Create two implementations with same prompt
        impl1 = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl1)
        await test_session.flush()

        impl2 = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl2)
        await test_session.commit()

        # Create a trace
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        # Should match the first implementation
        assert data["implementation_id"] == impl1.id

    @pytest.mark.asyncio
    async def test_trace_no_match_when_no_system_prompt(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that trace doesn't match when there's no system message."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace without system message
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] is None
        assert data["prompt_variables"] is None

    @pytest.mark.asyncio
    async def test_trace_matches_complex_multiline_prompt(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test matching with complex multiline prompts."""
        # Create an implementation with multiline template
        impl = Implementation(
            task_id=task.id,
            prompt="""You are {role}.
User: {name}
Department: {department}

Please assist with their requests.""",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace with actual values
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": """You are a senior developer.
User: Bob Smith
Department: Engineering

Please assist with their requests.""",
                },
                {"type": "message", "role": "user", "content": "I need help."},
            ],
            "result": "How can I help?",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] == impl.id
        assert data["prompt_variables"] == {
            "role": "a senior developer",
            "name": "Bob Smith",
            "department": "Engineering",
        }

    @pytest.mark.asyncio
    async def test_trace_no_match_different_project(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that implementations from different projects don't match."""
        # Create an implementation in the test project
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.commit()

        # Create a trace in a different project
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Different Project",  # Different project
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        # Should not match because it's a different project
        assert data["implementation_id"] is None
        assert data["prompt_variables"] is None
