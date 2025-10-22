"""Tests for requests HTTP wrapper."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import requests

from r4u.tracing.http.requests import (
    trace_session,
    trace_all,
    untrace_all,
    StreamingResponseWrapper,
    _build_trace_context,
    _finalize_trace,
    _is_streaming_request,
)
from r4u.client import HTTPTrace


@pytest.fixture
def mock_requests_prepared_request():
    """Create a mock requests PreparedRequest."""
    request = Mock(spec=requests.PreparedRequest)
    request.method = "POST"
    request.url = "https://api.example.com/test"
    request.headers = {"Content-Type": "application/json"}
    request.body = b'{"test": "data"}'
    return request


@pytest.fixture
def mock_requests_response():
    """Create a mock requests response."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.content = b'{"result": "success"}'
    return response


@pytest.fixture
def mock_streaming_response():
    """Create a mock streaming requests response."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.headers = {"Content-Type": "text/event-stream"}
    response.content = b"chunk1chunk2chunk3"

    # Mock streaming methods
    response.iter_content = Mock(return_value=iter([b"chunk1", b"chunk2", b"chunk3"]))
    response.iter_lines = Mock(return_value=iter([b"line1", b"line2", b"line3"]))

    return response


class TestBuildTraceContext:
    """Tests for _build_trace_context function."""

    def test_build_trace_context_with_post_request(
        self, mock_requests_prepared_request
    ):
        """Test building trace context from POST request."""
        ctx = _build_trace_context(mock_requests_prepared_request)

        assert ctx["method"] == "POST"
        assert ctx["url"] == "https://api.example.com/test"
        assert ctx["request_bytes"] == b'{"test": "data"}'
        assert ctx["request_headers"]["Content-Type"] == "application/json"
        assert isinstance(ctx["started_at"], datetime)

    def test_build_trace_context_with_get_request(self):
        """Test building trace context from GET request."""
        request = Mock(spec=requests.PreparedRequest)
        request.method = "GET"
        request.url = "https://api.example.com/users"
        request.headers = {}
        request.body = None

        ctx = _build_trace_context(request)

        assert ctx["method"] == "GET"
        assert ctx["url"] == "https://api.example.com/users"
        assert ctx["request_bytes"] == b""

    def test_build_trace_context_with_string_body(self):
        """Test building trace context with string body."""
        request = Mock(spec=requests.PreparedRequest)
        request.method = "POST"
        request.url = "https://api.example.com/test"
        request.headers = {}
        request.body = "string body"

        ctx = _build_trace_context(request)

        assert ctx["request_bytes"] == b"string body"

    def test_build_trace_context_lowercase_method(self):
        """Test that method is uppercased."""
        request = Mock(spec=requests.PreparedRequest)
        request.method = "post"
        request.url = "https://api.example.com/test"
        request.headers = {}
        request.body = b""

        ctx = _build_trace_context(request)

        assert ctx["method"] == "POST"


class TestFinalizeTrace:
    """Tests for _finalize_trace function."""

    def test_finalize_trace_successful_response(self, mock_requests_response):
        """Test finalizing trace with successful response."""
        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "POST",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b'{"test": "data"}',
            "request_headers": {"Content-Type": "application/json"},
        }

        trace = _finalize_trace(trace_ctx, mock_requests_response, None)

        assert isinstance(trace, HTTPTrace)
        assert trace.url == "https://api.example.com/test"
        assert trace.method == "POST"
        assert trace.status_code == 200
        assert trace.response == b'{"result": "success"}'
        assert trace.error is None

    def test_finalize_trace_with_error(self):
        """Test finalizing trace with error."""
        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        trace = _finalize_trace(trace_ctx, None, "Connection timeout")

        assert trace.status_code == 0
        assert trace.error == "Connection timeout"
        assert trace.response == b""

    def test_finalize_trace_has_timing(self):
        """Test trace has proper timing information."""
        started_at = datetime.now(timezone.utc)
        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": started_at,
            "request_bytes": b"",
            "request_headers": {},
        }

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.content = b""

        trace = _finalize_trace(trace_ctx, response, None)

        assert trace.started_at == started_at
        assert trace.completed_at >= started_at


class TestIsStreamingRequest:
    """Tests for _is_streaming_request function."""

    def test_is_streaming_with_stream_true(self):
        """Test detects streaming when stream=True."""
        assert _is_streaming_request({"stream": True}) is True

    def test_is_not_streaming_with_stream_false(self):
        """Test detects non-streaming when stream=False."""
        assert _is_streaming_request({"stream": False}) is False

    def test_is_not_streaming_without_stream_param(self):
        """Test defaults to non-streaming when no stream param."""
        assert _is_streaming_request({}) is False


class TestStreamingResponseWrapper:
    """Tests for StreamingResponseWrapper."""

    def test_wrapper_delegates_attributes(
        self, mock_requests_response, capturing_tracer
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
            mock_requests_response, trace_ctx, capturing_tracer
        )

        assert wrapper.status_code == 200
        assert wrapper.headers == mock_requests_response.headers

    def test_wrapper_content_property_collects_data(self, capturing_tracer):
        """Test wrapper.content property collects content and sends trace."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {"Content-Type": "text/plain"}
        response.content = b"test content"
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        content = wrapper.content

        assert content == b"test content"
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"test content"

    def test_wrapper_text_property_collects_data(self, capturing_tracer):
        """Test wrapper.text property collects content and sends trace."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.text = "test text"
        response.content = b"test text"
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        text = wrapper.text

        assert text == "test text"
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"test text"

    def test_wrapper_json_method_collects_data(self, capturing_tracer):
        """Test wrapper.json() collects content and sends trace."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.json = Mock(return_value={"result": "success"})
        response.content = b'{"result": "success"}'
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        json_data = wrapper.json()

        assert json_data == {"result": "success"}
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b'{"result": "success"}'

    def test_wrapper_iter_content_collects_chunks(self, capturing_tracer):
        """Test wrapper.iter_content() collects all chunks."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.iter_content = Mock(
            return_value=iter([b"chunk1", b"chunk2", b"chunk3"])
        )
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        chunks = list(wrapper.iter_content())

        assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].response == b"chunk1chunk2chunk3"

    def test_wrapper_iter_lines_collects_lines(self, capturing_tracer):
        """Test wrapper.iter_lines() collects all lines."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.iter_lines = Mock(return_value=iter([b"line1", b"line2", b"line3"]))
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        lines = list(wrapper.iter_lines())

        assert lines == [b"line1", b"line2", b"line3"]
        assert len(capturing_tracer.traces) == 1
        # Each line gets a newline appended
        assert capturing_tracer.traces[0].response == b"line1\nline2\nline3\n"

    def test_wrapper_handles_streaming_error(self, capturing_tracer, capsys):
        """Test wrapper handles errors during streaming."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.close = Mock()

        def failing_iter(*args, **kwargs):
            yield b"chunk1"
            raise Exception("Stream error")

        response.iter_content = Mock(return_value=failing_iter())

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)

        with pytest.raises(Exception, match="Stream error"):
            list(wrapper.iter_content())

        # Should still send trace with error
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].error == "Stream error"

    def test_wrapper_close_sends_trace(self, capturing_tracer):
        """Test wrapper.close() sends trace."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.close = Mock()

        trace_ctx = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "started_at": datetime.now(timezone.utc),
            "request_bytes": b"",
            "request_headers": {},
        }

        wrapper = StreamingResponseWrapper(response, trace_ctx, capturing_tracer)
        wrapper.close()

        assert len(capturing_tracer.traces) == 1
        response.close.assert_called_once()


class TestTraceSession:
    """Tests for trace_session function."""

    def test_trace_session_wraps_send_method(self, capturing_tracer):
        """Test trace_session wraps the send method."""
        session = requests.Session()
        original_send = session.send

        trace_session(session, capturing_tracer)

        assert session.send != original_send
        assert hasattr(session.send, "_r4u_patched")

    def test_trace_session_prevents_double_patching(self, capturing_tracer):
        """Test trace_session doesn't double-patch."""
        session = requests.Session()

        trace_session(session, capturing_tracer)
        patched_send = session.send

        trace_session(session, capturing_tracer)

        # Should be the same patched method
        assert session.send is patched_send

    def test_trace_session_captures_request(
        self, mock_requests_prepared_request, mock_requests_response, capturing_tracer
    ):
        """Test trace_session captures request data."""
        session = requests.Session()

        # Mock the original send method
        def mock_send(request, **kwargs):
            return mock_requests_response

        session.send = mock_send
        trace_session(session, capturing_tracer)

        # Make request
        response = session.send(mock_requests_prepared_request)

        assert response == mock_requests_response
        assert len(capturing_tracer.traces) == 1

        trace = capturing_tracer.traces[0]
        assert trace.method == "POST"
        assert trace.url == "https://api.example.com/test"
        assert trace.status_code == 200

    def test_trace_session_handles_exceptions(
        self, mock_requests_prepared_request, capturing_tracer
    ):
        """Test trace_session handles exceptions properly."""
        session = requests.Session()

        def mock_send_error(request, **kwargs):
            raise requests.RequestException("Connection failed")

        session.send = mock_send_error
        trace_session(session, capturing_tracer)

        with pytest.raises(requests.RequestException):
            session.send(mock_requests_prepared_request)

        # Should still create a trace with error
        assert len(capturing_tracer.traces) == 1
        assert capturing_tracer.traces[0].error == "Connection failed"

    def test_trace_session_handles_streaming_request(
        self, mock_requests_prepared_request, capturing_tracer
    ):
        """Test trace_session handles streaming requests."""
        session = requests.Session()

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {}
        response.content = b"test"
        response.close = Mock()

        def mock_send(request, **kwargs):
            return response

        session.send = mock_send
        trace_session(session, capturing_tracer)

        # Make streaming request
        result = session.send(mock_requests_prepared_request, stream=True)

        # Should return wrapped response
        assert isinstance(result, StreamingResponseWrapper)

        # Access content to complete streaming
        _ = result.content

        assert len(capturing_tracer.traces) == 1


class TestTraceAll:
    """Tests for trace_all functionality."""

    def test_trace_all_patches_constructor(self, capturing_tracer):
        """Test trace_all patches Session constructor."""
        # Store original constructor
        original_session_init = requests.Session.__init__

        trace_all(capturing_tracer)

        assert requests.Session.__init__ != original_session_init
        assert hasattr(requests.Session, "_r4u_constructor_patched")

        # Cleanup
        untrace_all()

    def test_trace_all_prevents_double_patching(self, capturing_tracer):
        """Test trace_all doesn't double-patch."""
        trace_all(capturing_tracer)
        patched_init = requests.Session.__init__

        trace_all(capturing_tracer)

        assert requests.Session.__init__ is patched_init

        # Cleanup
        untrace_all()

    def test_trace_all_auto_traces_new_sessions(self, capturing_tracer):
        """Test trace_all automatically traces newly created sessions."""
        trace_all(capturing_tracer)

        # Create new session
        session = requests.Session()

        # Should be automatically patched
        assert hasattr(session.send, "_r4u_patched")

        # Cleanup
        session.close()
        untrace_all()

    def test_untrace_all_restores_original_constructor(self, capturing_tracer):
        """Test untrace_all restores original constructor."""
        original_session_init = requests.Session.__init__

        trace_all(capturing_tracer)
        untrace_all()

        assert requests.Session.__init__ == original_session_init
        assert not hasattr(requests.Session, "_r4u_constructor_patched")

    def test_untrace_all_when_not_patched(self):
        """Test untrace_all handles case when not patched."""
        # Should not raise any errors
        untrace_all()

    def test_trace_all_uses_default_tracer_when_none(self):
        """Test trace_all uses default tracer when None provided."""
        with patch("r4u.tracing.http.requests.get_r4u_client") as mock_get_client:
            mock_tracer = Mock()
            mock_get_client.return_value = mock_tracer

            trace_all(None)

            mock_get_client.assert_called_once()

            # Cleanup
            untrace_all()


class TestEndToEndRequestsTracing:
    """End-to-end tests for requests tracing."""

    def test_full_request_lifecycle(self, capturing_tracer):
        """Test full request lifecycle with tracing."""
        session = requests.Session()
        trace_session(session, capturing_tracer)

        # Mock the actual HTTP call
        prepared_request = Mock(spec=requests.PreparedRequest)
        prepared_request.method = "GET"
        prepared_request.url = "https://api.example.com/data"
        prepared_request.headers = {"User-Agent": "test"}
        prepared_request.body = None

        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"data": "value"}'

        def mock_send(request, **kwargs):
            return response

        session.send = mock_send
        trace_session(session, capturing_tracer)

        result = session.send(prepared_request)

        assert result == response
        assert len(capturing_tracer.traces) == 1

        trace = capturing_tracer.traces[0]
        assert trace.method == "GET"
        assert trace.url == "https://api.example.com/data"
        assert trace.status_code == 200
        assert trace.response == b'{"data": "value"}'
        assert trace.error is None
