"""Tests for trace service."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.http_traces import HTTPTrace
from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.models.traces import Trace
from app.schemas.traces import TraceCreate
from app.services.traces_service import TracesService


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
    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id)
    test_session.add(task)
    await test_session.flush()
    return task


@pytest_asyncio.fixture
async def implementation(test_session: AsyncSession, task: Task) -> Implementation:
    """Create a test implementation."""
    impl = Implementation(
        task_id=task.id,
        prompt="Hello, {name}! You are user #{user_id}.",
        model="gpt-4",
        max_output_tokens=1000)
    test_session.add(impl)
    await test_session.flush()
    return impl


@pytest_asyncio.fixture
def traces_service() -> TracesService:
    """Create traces service instance."""
    return TracesService()


class TestTracesServiceCreate:
    """Test trace creation via service."""

    @pytest.mark.asyncio
    async def test_create_trace_with_auto_matching(
        self,
        test_session: AsyncSession,
        traces_service: TracesService,
        implementation: Implementation):
        """Test creating a trace that auto-matches an implementation."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {
                    "type": "message",
                    "role": "system",
                    "content": "Hello, Alice! You are user #42.",
                },
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi there!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.id is not None
        assert trace.implementation_id == implementation.id
        assert trace.prompt_variables == {"name": "Alice", "user_id": "42"}
        assert trace.model == "gpt-4"
        assert len(trace.output_items) == 1

        # Verify in database
        result = await test_session.execute(select(Trace).where(Trace.id == trace.id))
        db_trace = result.scalar_one()
        assert db_trace.implementation_id == implementation.id
        assert db_trace.prompt_variables == {"name": "Alice", "user_id": "42"}

    @pytest.mark.asyncio
    async def test_create_trace_with_explicit_implementation_id(
        self,
        test_session: AsyncSession,
        traces_service: TracesService,
        implementation: Implementation):
        """Test creating a trace with explicit implementation_id (no auto-matching)."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            implementation_id=implementation.id,  # Explicit
            input=[
                {
                    "type": "message",
                    "role": "system",
                    "content": "Different prompt that won't match.",
                },
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Response"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.implementation_id == implementation.id
        assert trace.prompt_variables is None  # No auto-matching happened

    @pytest.mark.asyncio
    async def test_create_trace_with_no_match(
        self,
        test_session: AsyncSession,
        traces_service: TracesService,
        project: Project):
        """Test creating a trace when no implementation matches."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {
                    "type": "message",
                    "role": "system",
                    "content": "This won't match any implementation.",
                },
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Response"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.id is not None
        assert trace.implementation_id is None
        assert trace.prompt_variables is None
        assert len(trace.output_items) == 1

    @pytest.mark.asyncio
    async def test_create_trace_with_new_project(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test creating a trace that auto-creates a new project."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="New Project",  # Doesn't exist yet
            input=[
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.id is not None
        assert trace.project_id is not None

        # Verify project was created
        result = await test_session.execute(
            select(Project).where(Project.name == "New Project"))
        project = result.scalar_one_or_none()
        assert project is not None
        assert trace.project_id == project.id

    @pytest.mark.asyncio
    async def test_create_trace_with_http_trace_id(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test creating a trace with http_trace_id."""
        # Create HTTP trace first
        http_trace = HTTPTrace(
            started_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 10, 15, 10, 0, 1, tzinfo=UTC),
            status_code=200,
            request="POST /v1/chat/completions",
            request_headers={},
            response='{"choices":[]}',
            response_headers={})
        test_session.add(http_trace)
        await test_session.flush()

        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(
            trace_data,
            test_session,
            http_trace_id=http_trace.id)

        assert trace.http_trace_id == http_trace.id

    @pytest.mark.asyncio
    async def test_create_trace_with_all_fields(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test creating a trace with all optional fields."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "system", "content": "You are helpful."},
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi there!"}]}],
            error=None,
            path="/api/chat",
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z",
            instructions="Be nice",
            prompt="Hello",
            temperature=0.7,
            tool_choice="auto",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cached_tokens=5,
            reasoning_tokens=2,
            finish_reason="stop",
            system_fingerprint="fp_123",
            response_schema={"type": "object"},
            trace_metadata={"custom": "data"})

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.model == "gpt-4"
        assert trace.path == "/api/chat"
        assert trace.instructions == "Be nice"
        assert trace.temperature == 0.7
        assert trace.prompt_tokens == 10
        assert trace.completion_tokens == 20
        assert trace.total_tokens == 30
        assert trace.cached_tokens == 5
        assert trace.reasoning_tokens == 2
        assert trace.finish_reason == "stop"
        assert trace.system_fingerprint == "fp_123"
        assert trace.response_schema == {"type": "object"}
        assert trace.trace_metadata == {"custom": "data"}

    @pytest.mark.asyncio
    async def test_create_trace_with_tools(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test creating a trace with tool definitions."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object"},
                    },
                },
            ])

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.tools is not None
        assert len(trace.tools) == 1
        assert trace.tools[0]["type"] == "function"
        assert trace.tools[0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_create_trace_with_reasoning(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test creating a trace with reasoning configuration."""
        from app.schemas.traces import Reasoning

        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z",
            reasoning=Reasoning(effort="high", summary="detailed"))

        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.reasoning is not None
        assert trace.reasoning["effort"] == "high"
        assert trace.reasoning["summary"] == "detailed"

    @pytest.mark.asyncio
    async def test_create_trace_matching_fails_gracefully(
        self,
        test_session: AsyncSession,
        traces_service: TracesService,
        implementation: Implementation,
        monkeypatch):
        """Test that trace creation succeeds even if matching fails."""
        from app.services import implementation_matcher

        # Mock the matching function to raise an exception
        async def mock_find_matching(*args, **kwargs):
            raise Exception("Matching failed!")

        monkeypatch.setattr(
            implementation_matcher,
            "find_matching_implementation",
            mock_find_matching)

        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "user", "content": "Hello!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        # Should not raise, trace should be created
        trace = await traces_service.create_trace(trace_data, test_session)

        assert trace.id is not None
        assert trace.implementation_id is None
        assert trace.prompt_variables is None

    @pytest.mark.asyncio
    async def test_create_trace_with_input_items(
        self,
        test_session: AsyncSession,
        traces_service: TracesService):
        """Test that input items are properly created."""
        trace_data = TraceCreate(
            model="gpt-4",
            project="Test Project",
            input=[
                {"type": "message", "role": "system", "content": "You are helpful."},
                {"type": "message", "role": "user", "content": "Hello!"},
                {"type": "message", "role": "assistant", "content": "Hi there!"},
            ],
            output=[{"type": "message", "id": "msg-1", "content": [{"type": "text", "text": "Hi there!"}]}],
            started_at="2025-10-15T10:00:00Z",
            completed_at="2025-10-15T10:00:01Z")

        trace = await traces_service.create_trace(trace_data, test_session)

        assert len(trace.input_items) == 3
        assert trace.input_items[0].position == 0
        assert trace.input_items[0].data["role"] == "system"
        assert trace.input_items[1].position == 1
        assert trace.input_items[1].data["role"] == "user"
        assert trace.input_items[2].position == 2
        assert trace.input_items[2].data["role"] == "assistant"
