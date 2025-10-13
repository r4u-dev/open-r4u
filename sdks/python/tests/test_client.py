"""Tests for the R4U client."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from r4u.client import R4UClient, TraceCreate, MessageCreate


class TestR4UClient:
    """Test cases for R4UClient."""

    def test_init(self):
        """Test client initialization."""
        client = R4UClient(api_url="http://test:8000", timeout=60.0)
        assert client.api_url == "http://test:8000"
        assert client.timeout == 60.0

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from API URL."""
        client = R4UClient(api_url="http://test:8000/")
        assert client.api_url == "http://test:8000"

    @patch('r4u.client.httpx.Client')
    def test_create_trace_sync(self, mock_httpx_client):
        """Test synchronous trace creation."""
        # Setup
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 1,
            "model": "gpt-3.5-turbo",
            "result": "Hello!",
            "error": None,
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:01",
            "messages": [
                {"role": "user", "content": "Hi", "id": 1},
                {"role": "assistant", "content": "Hello!", "id": 2}
            ]
        }
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value = mock_client_instance
        
        client = R4UClient()
        
        # Test
        result = client.create_trace(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"}
            ],
            result="Hello!"
        )
        
        # Verify
        assert result.id == 1
        assert result.model == "gpt-3.5-turbo"
        assert result.result == "Hello!"
        assert len(result.messages) == 2
        
        # Verify HTTP call
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert call_args[0][0] == "http://localhost:8000/traces"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    @patch('r4u.client.httpx.AsyncClient')
    async def test_create_trace_async(self, mock_httpx_async_client):
        """Test asynchronous trace creation."""
        # Setup
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 1,
            "model": "gpt-3.5-turbo",
            "result": "Hello!",
            "error": None,
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:01",
            "messages": [
                {"role": "user", "content": "Hi", "id": 1},
                {"role": "assistant", "content": "Hello!", "id": 2}
            ]
        }
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_async_client.return_value = mock_client_instance
        
        client = R4UClient()
        
        # Test
        result = await client.create_trace_async(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"}
            ],
            result="Hello!"
        )
        
        # Verify
        assert result.id == 1
        assert result.model == "gpt-3.5-turbo"
        assert result.result == "Hello!"
        assert len(result.messages) == 2

    def test_trace_create_schema(self):
        """Test TraceCreate schema."""
        now = datetime.utcnow()
        trace = TraceCreate(
            model="gpt-4",
            result="Test result",
            error=None,
            started_at=now,
            completed_at=now,
            messages=[
                MessageCreate(role="user", content="Hello"),
                MessageCreate(role="assistant", content="Hi there!")
            ]
        )
        
        assert trace.model == "gpt-4"
        assert trace.result == "Test result"
        assert trace.error is None
        assert len(trace.messages) == 2
        assert trace.messages[0].role == "user"
        assert trace.messages[1].content == "Hi there!"

    def test_message_create_schema(self):
        """Test MessageCreate schema."""
        message = MessageCreate(role="user", content="Test message")
        
        assert message.role == "user"
        assert message.content == "Test message"