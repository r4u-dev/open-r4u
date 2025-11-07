"""Tests for automatic implementation creation from similar traces."""

from unittest.mock import AsyncMock, MagicMock, patch

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
def mock_openai_client():
    """Mock the OpenAI client to avoid requiring API keys."""
    with patch("app.services.task_service.get_async_openai_client") as mock:
        # Create mock client
        mock_client = AsyncMock()

        # Create mock response with parsed output
        mock_response = MagicMock()
        mock_parsed = MagicMock()
        mock_parsed.name = "Auto-generated Task"
        mock_parsed.description = "Auto-generated task description from instructions"
        mock_response.output_parsed = mock_parsed

        # Set up the client's responses.parse method
        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        # Return the mock client
        mock.return_value = mock_client

        yield mock


class TestAutoCreateImplementation:
    """Test automatic implementation creation from similar traces."""

    @pytest.mark.asyncio
    async def test_auto_create_implementation_from_similar_traces(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that implementations are auto-created from similar traces."""
        # Create 3 similar traces (reaches min_cluster_size of 3)
        names = ["Alice", "Bob", "Charlie"]

        for name in names:
            payload = {
                "model": "gpt-4",
                "path": "/api/greet",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"Greet user {name} politely.",
                    },
                    {"type": "message", "role": "user", "content": "Hello!"},
                ],
                "result": f"Hello {name}!",
                "started_at": "2025-10-17T10:00:00Z",
                "completed_at": "2025-10-17T10:00:01Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that a task and implementation were created
        task_query = select(Task).where(Task.path == "/api/greet")
        result = await test_session.execute(task_query)
        task = result.scalar_one_or_none()

        assert task is not None, "Task should be auto-created"
        assert task.production_version_id is not None

        # Check that implementation has inferred template
        impl_query = select(Implementation).where(
            Implementation.id == task.production_version_id,
        )
        result = await test_session.execute(impl_query)
        impl = result.scalar_one()

        assert impl is not None
        assert "{{var_" in impl.prompt or "{var_" in impl.prompt, (
            "Implementation prompt should contain template variables"
        )

        # Check that all traces are linked to this implementation
        test_session.expunge_all()  # Force refresh from database
        trace_query = select(Trace).where(Trace.path == "/api/greet")
        result = await test_session.execute(trace_query)
        traces = result.scalars().all()

        assert len(traces) == 3
        for trace in traces:
            assert trace.implementation_id == impl.id

    @pytest.mark.asyncio
    async def test_no_auto_create_with_insufficient_traces(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that implementations are NOT created when there aren't enough traces."""
        # Create only 2 traces (below min_cluster_size of 3)
        for name in ["Alice", "Bob"]:
            payload = {
                "model": "gpt-4",
                "path": "/api/insufficient",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"Greet {name}.",
                    },
                ],
                "result": f"Hello {name}!",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that NO task was created
        task_query = select(Task).where(Task.path == "/api/insufficient")
        result = await test_session.execute(task_query)
        task = result.scalar_one_or_none()

        assert task is None, "Task should not be created with insufficient traces"

        # Traces should not have implementation_id
        trace_query = select(Trace).where(Trace.path == "/api/insufficient")
        result = await test_session.execute(trace_query)
        traces = result.scalars().all()

        for trace in traces:
            assert trace.implementation_id is None

    @pytest.mark.asyncio
    async def test_auto_create_with_exact_min_cluster_size(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that implementation is created exactly at min_cluster_size threshold."""
        # Create exactly 3 traces (exactly min_cluster_size)
        # Use similar messages that meet the 0.6 similarity threshold
        names = ["Alice", "Bob", "Charlie"]
        for name in names:
            payload = {
                "model": "gpt-4",
                "path": "/api/exact",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"Process user {name} request.",
                    },
                ],
                "result": "Done",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that task was created
        task_query = select(Task).where(Task.path == "/api/exact")
        result = await test_session.execute(task_query)
        task = result.scalar_one_or_none()

        assert task is not None

    @pytest.mark.asyncio
    async def test_auto_create_with_null_path(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that implementations ARE auto-created for traces with null paths."""
        # Create 3 traces without paths but with similar prompts
        for i in range(3):
            payload = {
                "model": "gpt-4",
                # No path
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a helpful assistant. Process general request number {i} carefully.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that a task WAS created (null paths can be grouped together)
        test_session.expire_all()
        task_query = select(Task).where(Task.path.is_(None))
        result = await test_session.execute(task_query)
        tasks = result.scalars().all()

        assert len(tasks) == 1
        task = tasks[0]
        assert task.path is None
        assert task.production_version_id is not None

        # Verify implementation was created
        impl_query = select(Implementation).where(
            Implementation.id == task.production_version_id,
        )
        result = await test_session.execute(impl_query)
        impl = result.scalar_one()
        assert impl is not None

        # All traces should be linked to this implementation
        trace_query = select(Trace).where(Trace.path.is_(None))
        result = await test_session.execute(trace_query)
        traces = result.scalars().all()
        assert len(traces) == 3
        for trace in traces:
            assert trace.implementation_id == impl.id

    @pytest.mark.asyncio
    async def test_null_paths_separate_from_non_null_paths(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that traces with null paths are grouped separately from traces with paths."""
        # Create 3 traces with null path
        for i in range(3):
            payload = {
                "model": "gpt-4",
                # No path (null)
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a general purpose assistant. Handle unspecified request number {i} with default behavior and standard protocols.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Create 3 traces with actual path
        for i in range(3):
            payload = {
                "model": "gpt-4",
                "path": "/api/specific",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a specialized API handler for specific endpoint. Execute operation number {i} following endpoint requirements and validation rules.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that 2 separate tasks were created
        test_session.expire_all()
        task_query = select(Task)
        result = await test_session.execute(task_query)
        tasks = result.scalars().all()

        assert len(tasks) == 2

        # One task should have null path, one should have /api/specific
        paths = {task.path for task in tasks}
        assert None in paths
        assert "/api/specific" in paths

        # Check traces are correctly separated
        null_path_traces_query = select(Trace).where(Trace.path.is_(None))
        result = await test_session.execute(null_path_traces_query)
        null_path_traces = result.scalars().all()
        assert len(null_path_traces) == 3

        specific_path_traces_query = select(Trace).where(Trace.path == "/api/specific")
        result = await test_session.execute(specific_path_traces_query)
        specific_path_traces = result.scalars().all()
        assert len(specific_path_traces) == 3

        # All null path traces should have same implementation_id
        null_impl_ids = {trace.implementation_id for trace in null_path_traces}
        assert len(null_impl_ids) == 1
        assert None not in null_impl_ids

        # All specific path traces should have same implementation_id
        specific_impl_ids = {trace.implementation_id for trace in specific_path_traces}
        assert len(specific_impl_ids) == 1
        assert None not in specific_impl_ids

        # The two implementation_ids should be different
        assert null_impl_ids != specific_impl_ids

    @pytest.mark.asyncio
    async def test_no_auto_create_without_system_prompt(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that implementations are not auto-created for traces without system prompts."""
        # Create 3 traces without system messages
        for i in range(3):
            payload = {
                "model": "gpt-4",
                "path": "/api/no-system",
                "input": [
                    {"type": "message", "role": "user", "content": f"Message {i}"},
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that no task was created (can't infer template without system prompt)
        task_query = select(Task).where(Task.path == "/api/no-system")
        result = await test_session.execute(task_query)
        task = result.scalar_one_or_none()

        assert task is None

    @pytest.mark.asyncio
    async def test_separate_implementations_for_different_paths(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that different paths create separate implementations."""
        # Create 3 traces for path A
        for name in ["Alice", "Bob", "Charlie"]:
            payload = {
                "model": "gpt-4",
                "path": "/api/greet",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a friendly greeter. Greet user {name} politely and warmly.",
                    },
                ],
                "result": f"Hello {name}!",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Create 3 traces for path B
        for city in ["London", "Paris", "Tokyo"]:
            payload = {
                "model": "gpt-4",
                "path": "/api/weather",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a weather assistant. Get the current weather forecast for {city}.",
                    },
                ],
                "result": "Sunny",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that 2 separate tasks were created
        test_session.expire_all()
        task_query = select(Task)
        result = await test_session.execute(task_query)
        tasks = result.scalars().all()

        assert len(tasks) == 2

        paths = {task.path for task in tasks}
        assert "/api/greet" in paths
        assert "/api/weather" in paths

    @pytest.mark.asyncio
    async def test_separate_implementations_for_different_models(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that different models create separate implementations."""
        # Create 3 traces with gpt-4
        for i in range(3):
            payload = {
                "model": "gpt-4",
                "path": "/api/test",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a helpful assistant. Process request number {i} carefully.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Create 3 traces with gpt-3.5-turbo
        for i in range(3):
            payload = {
                "model": "gpt-3.5-turbo",
                "path": "/api/test",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a helpful assistant. Process request number {i} carefully.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check implementations
        impl_query = select(Implementation)
        result = await test_session.execute(impl_query)
        implementations = result.scalars().all()

        # Should have 2 implementations (one per model)
        assert len(implementations) == 2

        models = {impl.model for impl in implementations}
        assert "openai/gpt-4" in models or "gpt-4" in models
        assert "openai/gpt-3.5-turbo" in models

    @pytest.mark.asyncio
    async def test_existing_implementation_not_replaced(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        project: Project,
        mock_openai_client,
    ):
        """Test that existing implementations are not replaced by auto-creation."""
        # Create a task and implementation manually
        task = Task(
            name="Manual Task",
            description="Test task with manual implementation",
            project_id=project.id,
            path="/api/manual",
        )
        test_session.add(task)
        await test_session.flush()

        impl = Implementation(
            task_id=task.id,
            prompt="Manual template {name}",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        task.production_version_id = impl.id
        await test_session.commit()

        # Create 3 traces that would match this implementation
        for name in ["Alice", "Bob", "Charlie"]:
            payload = {
                "model": "gpt-4",
                "path": "/api/manual",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"Manual template {name}",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that only 1 implementation exists (the original)
        impl_query = select(Implementation).where(Implementation.task_id == task.id)
        result = await test_session.execute(impl_query)
        implementations = result.scalars().all()

        assert len(implementations) == 1
        assert implementations[0].id == impl.id

    @pytest.mark.asyncio
    async def test_template_inference_with_complex_patterns(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that template inference works with complex patterns."""
        # Create traces with multiple variables
        test_cases = [
            ("Alice", "admin", "full"),
            ("Bob", "viewer", "read-only"),
            ("Charlie", "editor", "write"),
        ]

        for name, role, access in test_cases:
            payload = {
                "model": "gpt-4",
                "path": "/api/auth",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are an authorization system. User {name} has role {role} with {access} access level. Please verify their permissions.",
                    },
                ],
                "result": "Authorized",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Test Project",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that implementation was created with template
        test_session.expire_all()
        task_query = select(Task).where(Task.path == "/api/auth")
        result = await test_session.execute(task_query)
        task = result.scalar_one_or_none()

        assert task is not None
        assert task.production_version_id is not None

        impl_query = select(Implementation).where(
            Implementation.id == task.production_version_id,
        )
        result = await test_session.execute(impl_query)
        impl = result.scalar_one()

        # Template should have variable placeholders
        assert "authorization system" in impl.prompt
        assert "User" in impl.prompt
        assert "has role" in impl.prompt
        assert "access level" in impl.prompt
        # Should have variable markers
        assert "{{var_" in impl.prompt or "{var_" in impl.prompt

    @pytest.mark.asyncio
    async def test_project_isolation_in_auto_creation(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        mock_openai_client,
    ):
        """Test that auto-creation respects project boundaries."""
        # Create 3 traces in Project A
        for i in range(3):
            payload = {
                "model": "gpt-4",
                "path": "/api/test",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a helpful assistant for Project A. Process item number {i}.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Project A",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Create 3 traces in Project B (same path, same model)
        for i in range(3):
            payload = {
                "model": "gpt-4",
                "path": "/api/test",
                "input": [
                    {
                        "type": "message",
                        "role": "system",
                        "content": f"You are a helpful assistant for Project B. Process item number {i}.",
                    },
                ],
                "result": "Response",
                "started_at": "2025-10-17T10:00:00Z",
                "project": "Project B",
            }
            response = await client.post("/v1/traces", json=payload)
            assert response.status_code == 201

        # Check that 2 separate tasks were created (one per project)
        test_session.expire_all()
        task_query = select(Task).where(Task.path == "/api/test")
        result = await test_session.execute(task_query)
        tasks = result.scalars().all()

        assert len(tasks) == 2

        # Each task should belong to a different project
        project_ids = {task.project_id for task in tasks}
        assert len(project_ids) == 2
