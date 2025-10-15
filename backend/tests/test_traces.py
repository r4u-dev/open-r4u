"""Tests for trace API endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.traces import Trace


@pytest.mark.asyncio
class TestTraceEndpoints:
    """Test trace CRUD operations."""

    async def test_create_trace_with_default_project(self, client: AsyncClient, test_session: AsyncSession):
        """Test creating a trace with default project."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
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
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"

        # Verify project was created
        result = await test_session.execute(select(Project).where(Project.name == "Default Project"))
        project = result.scalar_one_or_none()
        assert project is not None
        assert project.name == "Default Project"

    async def test_create_trace_with_custom_project(self, client: AsyncClient, test_session: AsyncSession):
        """Test creating a trace with a custom project."""
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Test"}],
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
        result = await test_session.execute(select(Project).where(Project.name == "Custom Project"))
        project = result.scalar_one_or_none()
        assert project is not None
        assert data["project_id"] == project.id

    async def test_create_trace_with_multiple_messages(self, client: AsyncClient):
        """Test creating a trace with multiple messages."""
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "How are you?"},
            ],
            "result": "I'm doing well!",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:02Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert len(data["messages"]) == 4
        assert data["messages"][0]["role"] == "system"
        assert data["messages"][1]["role"] == "user"
        assert data["messages"][2]["role"] == "assistant"
        assert data["messages"][3]["role"] == "user"

    async def test_create_trace_with_tools(self, client: AsyncClient):
        """Test creating a trace with tool definitions."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Search for weather"}],
            "result": "Searching...",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:01Z",
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get weather information",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                        },
                    },
                }
            ],
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["tools"] is not None
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "get_weather"

    async def test_create_trace_with_tool_calls(self, client: AsyncClient):
        """Test creating a trace with tool calls in messages."""
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "What's the weather?"},
                {
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
                        }
                    ],
                },
                {
                    "role": "tool",
                    "content": "Sunny, 72F",
                    "tool_call_id": "call_123",
                },
            ],
            "result": "It's sunny and 72F in NYC",
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:03Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert len(data["messages"]) == 3
        assert data["messages"][1]["tool_calls"] is not None
        assert data["messages"][2]["tool_call_id"] == "call_123"

    async def test_create_trace_with_error(self, client: AsyncClient):
        """Test creating a trace with an error."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
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
            "messages": [{"role": "user", "content": "Test"}],
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
                "messages": [{"role": "user", "content": f"Message {i}"}],
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

    async def test_create_trace_minimal(self, client: AsyncClient):
        """Test creating a trace with minimal required fields."""
        payload = {
            "model": "gpt-4",
            "messages": [],
            "started_at": "2025-10-15T10:00:00Z",
        }

        response = await client.post("/traces", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["model"] == "gpt-4"
        assert data["result"] is None
        assert data["error"] is None
        assert data["messages"] == []

    async def test_create_trace_reuses_existing_project(self, client: AsyncClient, test_session: AsyncSession):
        """Test that creating traces with same project name reuses the project."""
        # Create first trace with project
        payload1 = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "First"}],
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
            "messages": [{"role": "user", "content": "Second"}],
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
        result = await test_session.execute(select(Project).where(Project.name == "Shared Project"))
        projects = result.scalars().all()
        assert len(projects) == 1

    async def test_trace_includes_all_fields(self, client: AsyncClient):
        """Test that trace response includes all expected fields."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
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
        assert "messages" in data
        assert "tools" in data
        assert "prompt_tokens" in data
        assert "completion_tokens" in data
        assert "total_tokens" in data
        assert "response_schema" in data
        assert "trace_metadata" in data

    async def test_create_trace_with_tokens_and_metadata(self, client: AsyncClient):
        """Test creating a trace with token counts, response schema, and metadata."""
        response_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        metadata = {
            "environment": "production",
            "user_id": "user123",
            "session_id": "session456",
            "custom_field": "custom_value"
        }
        
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Generate a person"}],
            "result": '{"name": "John", "age": 30}',
            "started_at": "2025-10-15T10:00:00Z",
            "completed_at": "2025-10-15T10:00:02Z",
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200,
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
        assert data["response_schema"] == response_schema
        assert data["trace_metadata"] == metadata
        assert data["trace_metadata"]["environment"] == "production"
        assert data["trace_metadata"]["user_id"] == "user123"

    async def test_create_trace_with_partial_tokens(self, client: AsyncClient):
        """Test creating a trace with only some token fields."""
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Quick test"}],
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
