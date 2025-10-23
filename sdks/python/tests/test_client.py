"""Tests for R4U client and HTTPTrace model."""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from r4u.client import (
    AbstractTracer,
    ConsoleTracer,
    HTTPTrace,
    R4UClient,
    get_r4u_client,
)


class TestHTTPTraceModel:
    """Tests for HTTPTrace Pydantic model."""

    def test_http_trace_creation_with_required_fields(self):
        """Test creating HTTPTrace with all required fields."""
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="POST",
            started_at=started,
            completed_at=completed,
            status_code=200,
            request=b'{"test": "data"}',
            request_headers={"Content-Type": "application/json"},
            response=b'{"result": "success"}',
            response_headers={"Content-Type": "application/json"},
        )

        assert trace.url == "https://api.example.com/test"
        assert trace.method == "POST"
        assert trace.started_at == started
        assert trace.completed_at == completed
        assert trace.status_code == 200
        assert trace.request == b'{"test": "data"}'
        assert trace.response == b'{"result": "success"}'
        assert trace.error is None
        assert trace.metadata == {}

    def test_http_trace_with_path(self):
        """Test creating HTTPTrace with path field."""
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="POST",
            path="module.py::main->query_llm->create",
            started_at=started,
            completed_at=completed,
            status_code=200,
            request=b'{"test": "data"}',
            request_headers={"Content-Type": "application/json"},
            response=b'{"result": "success"}',
            response_headers={"Content-Type": "application/json"},
        )

        assert trace.path == "module.py::main->query_llm->create"
        assert trace.url == "https://api.example.com/test"
        assert trace.method == "POST"

    def test_http_trace_with_error(self):
        """Test creating HTTPTrace with an error."""
        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=500,
            error="Internal Server Error",
            request=b"",
            request_headers={},
            response=b'{"error": "something went wrong"}',
            response_headers={},
        )

        assert trace.status_code == 500
        assert trace.error == "Internal Server Error"

    def test_http_trace_with_metadata(self):
        """Test creating HTTPTrace with custom metadata."""
        metadata = {"provider": "openai", "model": "gpt-4", "user_id": "123"}

        trace = HTTPTrace(
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=b"{}",
            request_headers={},
            response=b"{}",
            response_headers={},
            metadata=metadata,
        )

        assert trace.metadata == metadata
        assert trace.metadata["provider"] == "openai"

    def test_http_trace_serialization(self):
        """Test HTTPTrace can be serialized to JSON."""
        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=b"test",
            request_headers={"X-Test": "value"},
            response=b"response",
            response_headers={"Content-Type": "text/plain"},
        )

        # Should be able to serialize to dict
        trace_dict = trace.model_dump(mode="json")
        assert trace_dict["url"] == "https://api.example.com/test"
        assert trace_dict["method"] == "GET"
        assert trace_dict["status_code"] == 200

    def test_http_trace_various_http_methods(self):
        """Test HTTPTrace with different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        for method in methods:
            trace = HTTPTrace(
                url="https://api.example.com/test",
                method=method,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                status_code=200,
                request=b"",
                request_headers={},
                response=b"",
                response_headers={},
            )
            assert trace.method == method

    def test_http_trace_with_empty_bodies(self):
        """Test HTTPTrace with empty request/response bodies."""
        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=204,
            request=b"",
            request_headers={},
            response=b"",
            response_headers={},
        )

        assert trace.request == b""
        assert trace.response == b""
        assert trace.status_code == 204

    def test_http_trace_with_large_payloads(self):
        """Test HTTPTrace with large request/response payloads."""
        large_request = b"x" * 10000
        large_response = b"y" * 10000

        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="POST",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=large_request,
            request_headers={},
            response=large_response,
            response_headers={},
        )

        assert len(trace.request) == 10000
        assert len(trace.response) == 10000


class TestConsoleTracer:
    """Tests for ConsoleTracer."""

    def test_console_tracer_logs_trace(self, capsys):
        """Test ConsoleTracer prints trace to console."""
        tracer = ConsoleTracer()
        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=b"request",
            request_headers={},
            response=b"response",
            response_headers={},
        )

        tracer.log(trace)

        captured = capsys.readouterr()
        assert "https://api.example.com/test" in captured.out
        assert "GET" in captured.out
        assert "200" in captured.out

    def test_console_tracer_is_abstract_tracer(self):
        """Test ConsoleTracer implements AbstractTracer."""
        tracer = ConsoleTracer()
        assert isinstance(tracer, AbstractTracer)


class TestR4UClient:
    """Tests for R4UClient."""

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_initialization(self, mock_httpx_client):
        """Test R4UClient initializes correctly."""
        client = R4UClient(api_url="http://localhost:8000", timeout=30.0)

        assert client.api_url == "http://localhost:8000"
        mock_httpx_client.assert_called_once()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_initialization_strips_trailing_slash(self, mock_httpx_client):
        """Test R4UClient strips trailing slash from API URL."""
        client = R4UClient(api_url="http://localhost:8000/", timeout=30.0)

        assert client.api_url == "http://localhost:8000"

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_log_adds_to_queue(self, mock_httpx_client):
        """Test R4UClient.log() adds trace to queue."""
        client = R4UClient(api_url="http://localhost:8000")

        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=b"",
            request_headers={},
            response=b"",
            response_headers={},
        )

        client.log(trace)

        # Check that trace was added to queue
        assert not client._trace_queue.empty()
        queued_trace = client._trace_queue.get_nowait()
        assert queued_trace == trace

        client.stop_worker()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_worker_thread_starts(self, mock_httpx_client):
        """Test worker thread starts automatically."""
        client = R4UClient(api_url="http://localhost:8000")

        assert client._worker_thread is not None
        assert client._worker_thread.is_alive()

        client.stop_worker()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_sends_traces_batch(self, mock_httpx_client):
        """Test R4UClient sends traces in batches."""
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value = mock_client_instance

        client = R4UClient(api_url="http://localhost:8000")

        traces = [
            HTTPTrace(
                url="https://api.example.com/test1",
                method="GET",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                status_code=200,
                request=b"",
                request_headers={},
                response=b"",
                response_headers={},
            ),
            HTTPTrace(
                url="https://api.example.com/test2",
                method="POST",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                status_code=201,
                request=b"data",
                request_headers={},
                response=b"result",
                response_headers={},
            ),
        ]

        client._send_traces_batch(traces)

        # Should have called post twice (once per trace)
        assert mock_client_instance.post.call_count == 2

        client.stop_worker()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_handles_send_error(self, mock_httpx_client, capsys):
        """Test R4UClient handles errors when sending traces."""
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = Exception("Network error")
        mock_httpx_client.return_value = mock_client_instance

        client = R4UClient(api_url="http://localhost:8000")

        trace = HTTPTrace(
            url="https://api.example.com/test",
            method="GET",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status_code=200,
            request=b"",
            request_headers={},
            response=b"",
            response_headers={},
        )

        # Should not raise exception
        client._send_traces_batch([trace])

        # Should have printed error
        captured = capsys.readouterr()
        assert "Error sending trace" in captured.out

        client.stop_worker()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_stop_worker(self, mock_httpx_client):
        """Test R4UClient.stop_worker() stops the worker thread."""
        client = R4UClient(api_url="http://localhost:8000")

        assert client._worker_thread.is_alive()

        client.stop_worker()

        # Give it a moment to stop
        time.sleep(0.1)

        assert client._stop_worker.is_set()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_close(self, mock_httpx_client):
        """Test R4UClient.close() stops worker and closes HTTP client."""
        mock_client_instance = Mock()
        mock_httpx_client.return_value = mock_client_instance

        client = R4UClient(api_url="http://localhost:8000")

        client.close()

        assert client._stop_worker.is_set()
        mock_client_instance.close.assert_called_once()

    @patch("r4u.client.httpx.Client")
    def test_r4u_client_is_abstract_tracer(self, mock_httpx_client):
        """Test R4UClient implements AbstractTracer."""
        client = R4UClient(api_url="http://localhost:8000")
        assert isinstance(client, AbstractTracer)
        client.stop_worker()


class TestGetR4UClient:
    """Tests for get_r4u_client singleton."""

    @patch("r4u.client.R4UClient")
    def test_get_r4u_client_returns_singleton(self, mock_r4u_client_class):
        """Test get_r4u_client returns the same instance."""
        # Clear the cache first
        get_r4u_client.cache_clear()

        mock_instance = Mock()
        mock_r4u_client_class.return_value = mock_instance

        client1 = get_r4u_client()
        client2 = get_r4u_client()

        # Should return the same instance
        assert client1 is client2

        # Should only create one instance
        assert mock_r4u_client_class.call_count == 1

    @patch.dict("os.environ", {"R4U_API_URL": "http://custom:9000"})
    @patch("r4u.client.R4UClient")
    def test_get_r4u_client_uses_env_vars(self, mock_r4u_client_class):
        """Test get_r4u_client uses environment variables."""
        get_r4u_client.cache_clear()

        mock_instance = Mock()
        mock_r4u_client_class.return_value = mock_instance

        get_r4u_client()

        mock_r4u_client_class.assert_called_once_with(
            api_url="http://custom:9000", timeout=30.0,
        )

    @patch.dict(
        "os.environ", {"R4U_API_URL": "http://custom:9000", "R4U_TIMEOUT": "60.0"},
    )
    @patch("r4u.client.R4UClient")
    def test_get_r4u_client_uses_custom_timeout(self, mock_r4u_client_class):
        """Test get_r4u_client uses custom timeout from env."""
        get_r4u_client.cache_clear()

        mock_instance = Mock()
        mock_r4u_client_class.return_value = mock_instance

        get_r4u_client()

        mock_r4u_client_class.assert_called_once_with(
            api_url="http://custom:9000", timeout=60.0,
        )
