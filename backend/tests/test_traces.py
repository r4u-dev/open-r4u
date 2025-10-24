"""Tests for trace API endpoints."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.http_traces import HTTPTrace
from app.models.projects import Project
from app.models.traces import Trace


@pytest.mark.asyncio
class TestTraceEndpoints:
    """Test trace CRUD operations."""

    async def test_create_trace_with_default_project(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test creating a trace with default project."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Default Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model"] == "gpt-4"
        assert data["result"] == "Hi there!"
        assert data["project_id"] == 1  # First project
        assert len(data["input"]) == 1
        assert data["input"][0]["data"]["role"] == "user"
        assert data["input"][0]["data"]["content"] == "Hello"

        # Verify project was created
        result = await test_session.execute(
            select(Project).where(Project.name == "Default Project"),
        )
        project = result.scalar_one_or_none()
        assert project is not None
        assert project.name == "Default Project"

    async def test_create_trace_with_custom_project(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test creating a trace with a custom project."""
        payload = {
            "model": "gpt-3.5-turbo",
            "input": [{"type": "message", "role": "user", "content": "Test"}],
            "result": "Response",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Custom Project",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model"] == "gpt-3.5-turbo"

        # Verify project was auto-created
        result = await test_session.execute(
            select(Project).where(Project.name == "Custom Project"),
        )
        project = result.scalar_one_or_none()
        assert project is not None
        assert data["project_id"] == project.id

    async def test_create_trace_with_multiple_messages(self, client: AsyncClient):
        """Test creating a trace with multiple messages."""
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "system", "content": "You are helpful"},
                {"type": "message", "role": "user", "content": "Hello"},
                {"type": "message", "role": "assistant", "content": "Hi!"},
                {"type": "message", "role": "user", "content": "How are you?"},
            ],
            "result": "I'm doing well!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:02Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert len(data["input"]) == 4
        assert data["input"][0]["data"]["role"] == "system"
        assert data["input"][1]["data"]["role"] == "user"
        assert data["input"][2]["data"]["role"] == "assistant"
        assert data["input"][3]["data"]["role"] == "user"

    async def test_create_trace_with_tools(self, client: AsyncClient):
        """Test creating a trace with tool definitions."""
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Search for weather"},
            ],
            "result": "Searching...",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"},
                            },
                        },
                    },
                },
            ],
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["tools"] is not None
        assert len(data["tools"]) == 1
        assert data["tools"][0]["type"] == "function"
        assert data["tools"][0]["function"]["name"] == "get_weather"

    async def test_create_trace_with_tool_calls(self, client: AsyncClient):
        """Test creating a trace with tool calls."""
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "What's the weather?"},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "NYC"}',
                            },
                        },
                    ],
                },
                {
                    "type": "tool_result",
                    "call_id": "call_123",
                    "tool_name": "get_weather",
                    "result": "Sunny, 72F",
                },
            ],
            "result": "It's sunny and 72F in NYC",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:03Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert len(data["input"]) == 3
        assert data["input"][1]["data"]["tool_calls"] is not None
        assert data["input"][2]["data"]["call_id"] == "call_123"

    async def test_create_trace_with_error(self, client: AsyncClient):
        """Test creating a trace with an error."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Test"}],
            "error": "API rate limit exceeded",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["error"] == "API rate limit exceeded"
        assert data["result"] is None

    async def test_create_trace_with_path(self, client: AsyncClient):
        """Test creating a trace with a call path."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Test"}],
            "result": "Response",
            "path": "module.function:123 -> helpers.process:45",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["path"] == "module.function:123 -> helpers.process:45"

    async def test_list_traces(self, client: AsyncClient):
        """Test listing all traces."""
        # Create multiple traces
        for i in range(3):
            payload = {
                "model": f"model-{i}",
                "input": [
                    {"type": "message", "role": "user", "content": f"Message {i}"},
                ],
                "result": f"Result {i}",
                "started_at": f"2025-10-15T10:0{i}:00Z",
                "completed_at": f"2025-10-15T10:0{i}:01Z",
            }
            await client.post("/traces", json=payload)

        # List all traces
        response = await client.get("/traces")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3
        # Traces should be ordered by started_at desc (newest first)
        assert data[0]["model"] == "model-2"
        assert data[1]["model"] == "model-1"
        assert data[2]["model"] == "model-0"

    async def test_list_traces_empty(self, client: AsyncClient):
        """Test listing traces when none exist."""
        response = await client.get("/traces")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_traces_with_pagination(self, client: AsyncClient):
        """Test listing traces with pagination parameters."""
        # Create 50 traces
        for i in range(50):
            payload = {
                "model": f"model-{i}",
                "input": [
                    {"type": "message", "role": "user", "content": f"Message {i}"},
                ],
                "result": f"Result {i}",
                "started_at": f"2025-10-15T10:{i:02d}:00Z",
                "completed_at": f"2025-10-15T10:{i:02d}:01Z",
            }
            await client.post("/traces", json=payload)

        # Test default pagination (limit=25, offset=0)
        response = await client.get("/traces")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 25
        # Should get newest 25 traces (model-49 to model-25)
        assert data[0]["model"] == "model-49"
        assert data[24]["model"] == "model-25"

        # Test with custom limit
        response = await client.get("/traces?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["model"] == "model-49"
        assert data[9]["model"] == "model-40"

        # Test with offset
        response = await client.get("/traces?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["model"] == "model-39"
        assert data[9]["model"] == "model-30"

        # Test with larger offset
        response = await client.get("/traces?limit=10&offset=40")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["model"] == "model-9"
        assert data[9]["model"] == "model-0"

        # Test offset beyond available traces
        response = await client.get("/traces?limit=10&offset=50")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_traces_pagination_limits(self, client: AsyncClient):
        """Test pagination parameter validation."""
        # Create a few traces
        for i in range(5):
            payload = {
                "model": f"model-{i}",
                "input": [
                    {"type": "message", "role": "user", "content": f"Message {i}"},
                ],
                "result": f"Result {i}",
                "started_at": f"2025-10-15T10:0{i}:00Z",
            }
            await client.post("/traces", json=payload)

        # Test limit=1 (minimum)
        response = await client.get("/traces?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Test limit=100 (maximum)
        response = await client.get("/traces?limit=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # Only 5 traces available

        # Test invalid limit (should fail validation)
        response = await client.get("/traces?limit=0")
        assert response.status_code == 422  # Validation error

        response = await client.get("/traces?limit=101")
        assert response.status_code == 422  # Validation error

        # Test invalid offset (should fail validation)
        response = await client.get("/traces?offset=-1")
        assert response.status_code == 422  # Validation error

    async def test_create_trace_minimal(self, client: AsyncClient):
        """Test creating a trace with minimal required fields."""
        payload = {
            "model": "gpt-4",
            "input": [],
            "started_at": "2025-10-15T10:00:00Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model"] == "gpt-4"
        assert data["result"] is None
        assert data["error"] is None
        assert data["input"] == []

    async def test_create_trace_reuses_existing_project(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test that creating traces with same project name reuses the project."""
        # Create first trace with project
        payload1 = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "First"}],
            "result": "Response 1",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Shared Project",
        }
        response1 = await client.post("/traces", json=payload1)
        assert response1.status_code == 201
        project_id_1 = response1.json()["project_id"]

        # Create second trace with same project name
        payload2 = {
            "model": "gpt-3.5-turbo",
            "input": [{"type": "message", "role": "user", "content": "Second"}],
            "result": "Response 2",
            "started_at": "2025-10-15T10:01:00Z",
            "completed_at": "2025-10-15T10:01:01Z",
            "project": "Shared Project",
        }
        response2 = await client.post("/traces", json=payload2)
        assert response2.status_code == 201
        project_id_2 = response2.json()["project_id"]

        # Both traces should use the same project
        assert project_id_1 == project_id_2

        # Verify only one project was created
        result = await test_session.execute(
            select(Project).where(Project.name == "Shared Project"),
        )
        projects = result.scalars().all()
        assert len(projects) == 1

    async def test_trace_includes_all_fields(self, client: AsyncClient):
        """Test that trace response includes all expected fields."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Test"}],
            "result": "Response",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        # Check all expected fields are present
        assert "id" in data
        assert "project_id" in data
        assert "model" in data
        assert "result" in data
        assert "error" in data
        assert "path" in data
        assert "started_at" in data
        assert "completed_at" in data
        assert "input" in data
        assert "tools" in data
        assert "instructions" in data
        assert "prompt" in data
        assert "temperature" in data
        assert "tool_choice" in data
        assert "prompt_tokens" in data
        assert "completion_tokens" in data
        assert "total_tokens" in data
        assert "cached_tokens" in data
        assert "reasoning_tokens" in data
        assert "finish_reason" in data
        assert "system_fingerprint" in data
        assert "reasoning" in data
        assert "response_schema" in data
        assert "trace_metadata" in data

    async def test_create_trace_with_tokens_and_metadata(self, client: AsyncClient):
        """Test creating a trace with token counts, response schema, and metadata."""
        response_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }

        metadata = {
            "environment": "production",
            "user_id": "user123",
            "session_id": "session456",
            "custom_field": "custom_value",
        }

        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Generate a person"},
            ],
            "result": '{"name": "John", "age": 30}',
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:02Z",
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200,
            "cached_tokens": 10,
            "reasoning_tokens": 5,
            "finish_reason": "stop",
            "system_fingerprint": "fp_12345",
            "reasoning": {"effort": "medium", "summary": "auto"},
            "response_schema": response_schema,
            "trace_metadata": metadata,
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model"] == "gpt-4"
        assert data["prompt_tokens"] == 150
        assert data["completion_tokens"] == 50
        assert data["total_tokens"] == 200
        assert data["cached_tokens"] == 10
        assert data["reasoning_tokens"] == 5
        assert data["finish_reason"] == "stop"
        assert data["system_fingerprint"] == "fp_12345"
        assert data["reasoning"]["effort"] == "medium"
        assert data["reasoning"]["summary"] == "auto"
        assert data["response_schema"] == response_schema
        assert data["trace_metadata"] == metadata
        assert data["trace_metadata"]["environment"] == "production"
        assert data["trace_metadata"]["user_id"] == "user123"

    async def test_create_trace_with_partial_tokens(self, client: AsyncClient):
        """Test creating a trace with only some token fields."""
        payload = {
            "model": "gpt-3.5-turbo",
            "input": [{"type": "message", "role": "user", "content": "Quick test"}],
            "result": "Quick response",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "total_tokens": 100,  # Only total_tokens provided
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["total_tokens"] == 100
        assert data["prompt_tokens"] is None
        assert data["completion_tokens"] is None

    async def test_create_trace_with_implementation_id(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test creating a trace with an associated implementation_id."""
        from app.models.tasks import Implementation, Task

        # First, create a project
        project = Project(name="Test Project")
        test_session.add(project)
        await test_session.flush()

        # Create a task
        task = Task(
            project_id=project.id,
        )
        test_session.add(task)
        await test_session.flush()

        # Create implementation
        implementation = Implementation(
            task_id=task.id,
            prompt="What is the weather?",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(implementation)
        await test_session.flush()

        task.production_version_id = implementation.id
        await test_session.commit()

        # Create a trace with the implementation_id
        payload = {
            "model": "gpt-4",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": "What is the weather in NYC?",
                },
            ],
            "result": "It's sunny and 72F",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "project": "Test Project",
            "implementation_id": implementation.id,
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] == implementation.id
        assert data["model"] == "gpt-4"

        # Verify the trace is linked to the implementation in the database
        result = await test_session.execute(
            select(Trace).where(Trace.id == data["id"]),
        )
        trace = result.scalar_one()
        assert trace.implementation_id == implementation.id

    async def test_create_trace_without_implementation_id(self, client: AsyncClient):
        """Test creating a trace without an implementation_id (should be None)."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Test"}],
            "result": "Response",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["implementation_id"] is None

    async def test_create_trace_with_mixed_input_types(self, client: AsyncClient):
        """Test creating a trace with different input item types."""
        payload = {
            "model": "gpt-4",
            "input": [
                {"type": "message", "role": "user", "content": "Analyze this image"},
                {
                    "type": "image",
                    "url": "https://example.com/image.jpg",
                    "mime_type": "image/jpeg",
                },
                {
                    "type": "tool_call",
                    "id": "call_456",
                    "tool_name": "analyze_image",
                    "arguments": {"url": "https://example.com/image.jpg"},
                },
                {
                    "type": "tool_result",
                    "call_id": "call_456",
                    "tool_name": "analyze_image",
                    "result": {"objects": ["cat", "dog"]},
                },
                {
                    "type": "mcp_tool_call",
                    "id": "mcp_789",
                    "server": "image-server",
                    "tool_name": "get_metadata",
                    "arguments": {"image_url": "https://example.com/image.jpg"},
                },
                {
                    "type": "mcp_tool_result",
                    "call_id": "mcp_789",
                    "server": "image-server",
                    "tool_name": "get_metadata",
                    "result": {"width": 1920, "height": 1080},
                },
            ],
            "result": "The image contains a cat and a dog",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:05Z",
            "finish_reason": "stop",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert len(data["input"]) == 6
        assert data["input"][0]["type"] == "message"
        assert data["input"][1]["type"] == "image"
        assert data["input"][2]["type"] == "tool_call"
        assert data["input"][3]["type"] == "tool_result"
        assert data["input"][4]["type"] == "mcp_tool_call"
        assert data["input"][5]["type"] == "mcp_tool_result"
        assert data["finish_reason"] == "stop"

    async def test_create_trace_with_request_parameters(self, client: AsyncClient):
        """Test creating a trace with request parameters."""
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Write a poem"}],
            "instructions": "You are a creative poet. Write in haiku format.",
            "prompt": "Write a haiku about autumn",
            "temperature": 0.8,
            "tool_choice": "auto",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_rhymes",
                        "description": "Get rhyming words",
                        "parameters": {
                            "type": "object",
                            "properties": {"word": {"type": "string"}},
                            "required": ["word"],
                        },
                    },
                },
            ],
            "result": "Autumn leaves fall down\nCrisp air whispers through the trees\nNature's canvas glows",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:03Z",
            "prompt_tokens": 45,
            "completion_tokens": 20,
            "total_tokens": 65,
            "finish_reason": "stop",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["instructions"] == "You are a creative poet. Write in haiku format."
        assert data["prompt"] == "Write a haiku about autumn"
        assert data["temperature"] == 0.8
        assert data["tool_choice"] == {"type": "auto"}
        assert data["tools"] is not None
        assert len(data["tools"]) == 1
        assert data["tools"][0]["type"] == "function"
        assert data["tools"][0]["function"]["name"] == "get_rhymes"

    async def test_create_trace_with_reasoning(self, client: AsyncClient):
        """Test creating a trace with reasoning content."""
        payload = {
            "model": "o1-preview",
            "input": [
                {"type": "message", "role": "user", "content": "Solve: 2x + 5 = 13"},
                {"type": "message", "role": "assistant", "content": "x = 4"},
            ],
            "reasoning": {
                "effort": "high",
                "summary": "auto",
            },
            "result": "x = 4",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:05Z",
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "reasoning_tokens": 1500,
            "total_tokens": 1530,
            "finish_reason": "stop",
            "temperature": 1.0,
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["reasoning"] is not None
        assert data["reasoning"]["effort"] == "high"
        assert data["reasoning"]["summary"] == "auto"
        assert data["reasoning_tokens"] == 1500
        assert data["temperature"] == 1.0

    async def test_get_trace_http_trace(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test fetching HTTP trace data for a trace."""
        # First create an HTTP trace
        http_trace = HTTPTrace(
            started_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2025, 10, 15, 10, 0, 1, tzinfo=UTC),
            status_code=200,
            error=None,
            request='{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}',
            request_headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer sk-xxx",
            },
            response='{"id": "chatcmpl-123", "choices": [{"message": {"content": "Hi there!"}}]}',
            response_headers={"Content-Type": "application/json"},
            http_metadata={},
        )
        test_session.add(http_trace)
        await test_session.flush()

        # Create a trace with the HTTP trace
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }
        response = await client.post("/traces", json=payload)
        assert response.status_code == 201
        trace_data = response.json()
        trace_id = trace_data["id"]

        # Update the trace to link it to the HTTP trace
        result = await test_session.execute(select(Trace).where(Trace.id == trace_id))
        trace = result.scalar_one()
        trace.http_trace_id = http_trace.id
        await test_session.commit()

        # Fetch the HTTP trace via the endpoint
        response = await client.get(f"/traces/{trace_id}/http-trace")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == http_trace.id
        assert data["status_code"] == 200
        assert (
            data["request"]
            == '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'
        )
        assert (
            data["response"]
            == '{"id": "chatcmpl-123", "choices": [{"message": {"content": "Hi there!"}}]}'
        )
        assert data["request_headers"]["Content-Type"] == "application/json"
        assert data["response_headers"]["Content-Type"] == "application/json"

    async def test_get_trace_http_trace_not_found(self, client: AsyncClient):
        """Test fetching HTTP trace for non-existent trace."""
        response = await client.get("/traces/99999/http-trace")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_trace_http_trace_no_http_trace(
        self,
        client: AsyncClient,
    ):
        """Test fetching HTTP trace for trace without HTTP trace."""
        # Create a trace without HTTP trace
        payload = {
            "model": "gpt-4",
            "input": [{"type": "message", "role": "user", "content": "Hello"}],
            "result": "Hi there!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
        }
        response = await client.post("/traces", json=payload)
        assert response.status_code == 201
        trace_id = response.json()["id"]

        # Try to fetch HTTP trace
        response = await client.get(f"/traces/{trace_id}/http-trace")
        assert response.status_code == 404
        assert "no associated http trace" in response.json()["detail"].lower()
