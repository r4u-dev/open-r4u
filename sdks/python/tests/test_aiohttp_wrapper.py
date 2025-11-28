"""Tests for aiohttp HTTP wrapper."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from r4u.tracing.http.aiohttp import (
    StreamingResponseWrapper,
    _is_streaming_request,
    trace_all,
    trace_async_client,
    untrace_all,
)


@pytest.fixture
def mock_aiohttp_response():
    """Create a mock aiohttp response."""
    response = Mock(spec=aiohttp.ClientResponse)
    response.status = 200
    response.headers = {"Content-Type": "application/json"}
    response.read = AsyncMock(return_value=b'{"result": "success"}')
    response.text = AsyncMock(return_value='{"result": "success"}')
    response.json = AsyncMock(return_value={"result": "success"})
    response.close = AsyncMock()
    return response


@pytest.fixture
def mock_streaming_response():
    """Create a mock streaming aiohttp response."""
    response = Mock(spec=aiohttp.ClientResponse)
    response.status = 200
    response.headers = {"Content-Type": "text/event-stream"}
    response.close = AsyncMock()

    # Mock content attribute with streaming methods
    content = Mock()

    async def mock_iter_chunked(chunk_size=8192):
        for chunk in [b"chunk1", b"chunk2", b"chunk3"]:
            yield chunk

    async def mock_iter_any():
        for chunk in [b"data1", b"data2"]:
            yield chunk

    async def mock_iter_line():
        for line in [b"line1", b"line2"]:
            yield line

    content.iter_chunked = mock_iter_chunked
    content.iter_any = mock_iter_any
    content.iter_line = mock_iter_line

    response.content = content
    response.read = AsyncMock(return_value=b"full content")

    return response


class TestIsStreamingRequest:
    """Tests for _is_streaming_request function."""

    def test_always_returns_true(self):
        """Test that aiohttp wrapper always returns True for streaming."""
        # aiohttp doesn't have a stream parameter, so we always wrap responses
        assert _is_streaming_request({}) is True
        assert _is_streaming_request({"stream": True}) is True
        assert _is_streaming_request({"stream": False}) is True


class TestStreamingResponseWrapper:
    """Tests for StreamingResponseWrapper."""

    def test_wrapper_delegates_attributes(
        self, mock_aiohttp_response, capturing_tracer,
    ):
        """Test wrapper delegates attributes to original response."""
        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(
            mock_aiohttp_response, trace_ctx, capturing_tracer,
        )

        assert wrapper.status == 200
        assert wrapper.headers == mock_aiohttp_response.headers

    @pytest.mark.asyncio
    async def test_wrapper_read_collects_content(self, capturing_tracer):
        """Test wrapper.read() collects content and sends trace."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {"Content-Type": "text/plain"}
        response.read = AsyncMock(return_value=b"test content")
        response.close = AsyncMock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        content = await wrapper.read()

        assert content == b"test content"
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"test content"

    @pytest.mark.asyncio
    async def test_wrapper_text_collects_content(self, capturing_tracer):
        """Test wrapper.text() collects content and sends trace."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.text = AsyncMock(return_value="test text")
        response.close = AsyncMock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        text = await wrapper.text()

        assert text == "test text"
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"test text"

    @pytest.mark.asyncio
    async def test_wrapper_json_collects_content(self, capturing_tracer):
        """Test wrapper.json() collects content and sends trace."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.json = AsyncMock(return_value={"result": "success"})
        response.read = AsyncMock(return_value=b'{"result": "success"}')
        response.close = AsyncMock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        json_data = await wrapper.json()

        assert json_data == {"result": "success"}
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b'{"result": "success"}'

    @pytest.mark.asyncio
    async def test_wrapper_iter_chunked_collects_chunks(self, capturing_tracer):
        """Test wrapper.iter_chunked() collects all chunks."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.close = AsyncMock()

        content = Mock()

        async def mock_iter_chunked(chunk_size=8192):
            for chunk in [b"chunk1", b"chunk2", b"chunk3"]:
                yield chunk

        content.iter_chunked = mock_iter_chunked
        response.content = content

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        chunks = []
        async for chunk in wrapper.iter_chunked():
            chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"chunk1chunk2chunk3"

    @pytest.mark.asyncio
    async def test_wrapper_iter_any_collects_chunks(self, capturing_tracer):
        """Test wrapper.iter_any() collects all chunks."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.close = AsyncMock()

        content = Mock()

        async def mock_iter_any():
            for chunk in [b"data1", b"data2", b"data3"]:
                yield chunk

        content.iter_any = mock_iter_any
        response.content = content

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        chunks = []
        async for chunk in wrapper.iter_any():
            chunks.append(chunk)

        assert chunks == [b"data1", b"data2", b"data3"]
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"data1data2data3"

    @pytest.mark.asyncio
    async def test_wrapper_iter_line_collects_lines(self, capturing_tracer):
        """Test wrapper.iter_line() collects all lines."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.close = AsyncMock()

        content = Mock()

        async def mock_iter_line():
            for line in [b"line1", b"line2", b"line3"]:
                yield line

        content.iter_line = mock_iter_line
        response.content = content

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        lines = []
        async for line in wrapper.iter_line():
            lines.append(line)

        assert lines == [b"line1", b"line2", b"line3"]
        assert len(capturing_tracer.traces) == 1
        # Each line gets a newline appended
        assert capturing_tracer.traces[0].response == b"line1\nline2\nline3\n"

    @pytest.mark.asyncio
    async def test_wrapper_handles_streaming_error(self, capturing_tracer, capsys):
        """Test wrapper handles errors during streaming."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.close = AsyncMock()

        content = Mock()

        async def failing_iter():
            yield b"chunk1"
            raise Exception("Stream error")

        content.iter_chunked = lambda chunk_size=8192: failing_iter()
        response.content = content

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        with pytest.raises(Exception, match="Stream error"):
            async for chunk in wrapper.iter_chunked():
                pass

        # Should still send trace with error
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].error == "Stream error"

    @pytest.mark.asyncio
    async def test_wrapper_close_sends_trace(self, capturing_tracer):
        """Test wrapper.close() sends trace."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.close = AsyncMock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        await wrapper.close()

        assert len(capturing_tracer.traces) == 1
        response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_wrapper_prevents_duplicate_traces(self, capturing_tracer):
        """Test wrapper doesn't send trace multiple times."""
        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {}
        response.read = AsyncMock(return_value=b"content")
        response.close = AsyncMock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        # Access content multiple times
        await wrapper.read()
        await wrapper.close()

        # Should only send one trace
        assert len(capturing_tracer.traces) == 1


class TestTraceAsyncClient:
    """Tests for trace_async_client function."""

    @pytest.mark.asyncio
    async def test_trace_async_client_wraps_request_method(self, capturing_tracer):
        """Test trace_async_client wraps the _request method."""
        session = aiohttp.ClientSession()
        original_request = session._request

        trace_async_client(session, capturing_tracer)

        assert session._request != original_request
        assert hasattr(session._request, "_r4u_patched")

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_trace_async_client_prevents_double_patching(self, capturing_tracer):
        """Test trace_async_client doesn't double-patch."""
        session = aiohttp.ClientSession()

        trace_async_client(session, capturing_tracer)
        patched_request = session._request

        trace_async_client(session, capturing_tracer)

        # Should be the same patched method
        assert session._request is patched_request

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_trace_async_client_captures_request(
        self, mock_aiohttp_response, capturing_tracer,
    ):
        """Test trace_async_client captures request data."""
        session = aiohttp.ClientSession()

        # Mock the original _request method
        async def mock_request(method, url, **kwargs):
            return mock_aiohttp_response

        session._request = mock_request
        trace_async_client(session, capturing_tracer)

        # Make request
        response = await session._request(
            "POST", "https://api.example.com/test", data=b'{"test": "data"}',
        )

        # Response should be wrapped
        assert isinstance(response, StreamingResponseWrapper)

        # Access content to complete streaming
        await response.read()

        assert len(capturing_tracer.traces) == 1

        trace = capturing_tracer.traces[0]
        assert trace.method == "POST"
        assert trace.url == "https://api.example.com/test"
        assert trace.status_code == 200

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_trace_async_client_handles_exceptions(self, capturing_tracer):
        """Test trace_async_client handles exceptions properly."""
        session = aiohttp.ClientSession()

        async def mock_request_error(method, url, **kwargs):
            raise aiohttp.ClientError("Connection failed")

        session._request = mock_request_error
        trace_async_client(session, capturing_tracer)

        with pytest.raises(aiohttp.ClientError):
            await session._request("GET", "https://api.example.com/test")

        # Should still create a trace with error
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].error == "Connection failed"

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_trace_async_client_with_json_data(
        self, mock_aiohttp_response, capturing_tracer,
    ):
        """Test trace_async_client with JSON data."""
        session = aiohttp.ClientSession()

        async def mock_request(method, url, **kwargs):
            return mock_aiohttp_response

        session._request = mock_request
        trace_async_client(session, capturing_tracer)

        # Make request with json parameter
        response = await session._request(
            "POST", "https://api.example.com/test", json={"key": "value"},
        )

        assert isinstance(response, StreamingResponseWrapper)

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_trace_async_client_with_headers(
        self, mock_aiohttp_response, capturing_tracer,
    ):
        """Test trace_async_client captures request headers."""
        session = aiohttp.ClientSession()

        async def mock_request(method, url, **kwargs):
            return mock_aiohttp_response

        session._request = mock_request
        trace_async_client(session, capturing_tracer)

        # Make request with headers
        response = await session._request(
            "GET",
            "https://api.example.com/test",
            headers={"Authorization": "Bearer token", "X-Custom": "value"},
        )

        await response.read()

        assert len(capturing_tracer.traces) == 1
        trace = capturing_tracer.traces[0]
        assert trace.request_headers.get("Authorization") == "[REDACTED]"
        assert trace.request_headers.get("X-Custom") == "value"

        # Cleanup
        await session.close()


class TestTraceAll:
    """Tests for trace_all functionality."""

    def test_trace_all_patches_constructor(self, capturing_tracer):
        """Test trace_all patches ClientSession constructor."""
        # Store original constructor
        original_init = aiohttp.ClientSession.__init__

        trace_all(capturing_tracer)

        assert aiohttp.ClientSession.__init__ != original_init
        assert hasattr(aiohttp.ClientSession, "_r4u_constructor_patched")

        # Cleanup
        untrace_all()

    def test_trace_all_prevents_double_patching(self, capturing_tracer):
        """Test trace_all doesn't double-patch."""
        trace_all(capturing_tracer)
        patched_init = aiohttp.ClientSession.__init__

        trace_all(capturing_tracer)

        assert aiohttp.ClientSession.__init__ is patched_init

        # Cleanup
        untrace_all()

    @pytest.mark.asyncio
    async def test_trace_all_auto_traces_new_sessions(self, capturing_tracer):
        """Test trace_all automatically traces newly created sessions."""
        trace_all(capturing_tracer)

        # Create new session
        session = aiohttp.ClientSession()

        # Should be automatically patched
        assert hasattr(session._request, "_r4u_patched")

        # Cleanup
        await session.close()
        untrace_all()

    def test_untrace_all_restores_original_constructor(self, capturing_tracer):
        """Test untrace_all restores original constructor."""
        # Make sure we start clean
        if hasattr(aiohttp.ClientSession, "_r4u_constructor_patched"):
            untrace_all()

        original_init = aiohttp.ClientSession.__init__

        trace_all(capturing_tracer)
        untrace_all()

        assert aiohttp.ClientSession.__init__ == original_init
        assert not hasattr(aiohttp.ClientSession, "_r4u_constructor_patched")

    def test_untrace_all_when_not_patched(self):
        """Test untrace_all handles case when not patched."""
        # Should not raise any errors
        untrace_all()



class TestEndToEndAiohttpTracing:
    """End-to-end tests for aiohttp tracing."""

    @pytest.mark.asyncio
    async def test_full_request_lifecycle(self, capturing_tracer):
        """Test full request lifecycle with tracing."""
        session = aiohttp.ClientSession()

        response = Mock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.read = AsyncMock(return_value=b'{"data": "value"}')
        response.close = AsyncMock()

        async def mock_request(method, url, **kwargs):
            return response

        session._request = mock_request
        trace_async_client(session, capturing_tracer)

        result = await session._request("GET", "https://api.example.com/data")

        assert isinstance(result, StreamingResponseWrapper)

        # Read content to complete trace
        content = await result.read()

        assert content == b'{"data": "value"}'
        assert len(capturing_tracer.traces) == 1

        trace = capturing_tracer.traces[0]
        assert trace.method == "GET"
        assert trace.url == "https://api.example.com/data"
        assert trace.status_code == 200
        assert trace.response == b'{"data": "value"}'
        assert trace.error is None

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_multiple_requests(self, capturing_tracer):
        """Test multiple requests are all traced."""
        session = aiohttp.ClientSession()

        call_count = 0

        async def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            response = Mock(spec=aiohttp.ClientResponse)
            response.status = 200
            response.headers = {}
            response.read = AsyncMock(return_value=f"response{call_count}".encode())
            response.close = AsyncMock()
            return response

        session._request = mock_request
        trace_async_client(session, capturing_tracer)

        # Make multiple requests
        for i in range(3):
            response = await session._request("GET", f"https://api.example.com/test{i}")
            await response.read()

        assert len(capturing_tracer.traces) == 3
        assert capturing_tracer.traces[0].url == "https://api.example.com/test0"
        assert capturing_tracer.traces[1].url == "https://api.example.com/test1"
        assert capturing_tracer.traces[2].url == "https://api.example.com/test2"

        # Cleanup
        await session.close()
