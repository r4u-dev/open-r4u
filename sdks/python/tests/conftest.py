"""Pytest configuration and shared fixtures for R4U SDK tests."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from r4u.client import AbstractTracer, HTTPTrace
from r4u.tracing.http.filters import URLFilter, set_global_filter


@pytest.fixture
def mock_tracer():
    """Create a mock tracer that captures logged traces."""
    tracer = Mock(spec=AbstractTracer)
    tracer.logged_traces = []

    def log_trace(trace: HTTPTrace):
        tracer.logged_traces.append(trace)

    tracer.log.side_effect = log_trace
    return tracer


@pytest.fixture
def sample_http_trace():
    """Create a sample HTTPTrace for testing."""
    return HTTPTrace(
        url="https://api.example.com/test",
        method="POST",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status_code=200,
        error=None,
        request=b'{"test": "data"}',
        request_headers={"Content-Type": "application/json"},
        response=b'{"result": "success"}',
        response_headers={"Content-Type": "application/json"},
        metadata={},
    )


@pytest.fixture
def sample_request_data():
    """Sample request data for testing."""
    return {
        "url": "https://api.example.com/endpoint",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer token",
        },
        "body": b'{"key": "value"}',
    }


@pytest.fixture
def sample_response_data():
    """Sample response data for testing."""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "body": b'{"status": "ok"}',
    }


@pytest.fixture
def streaming_response_data():
    """Sample streaming response data for testing."""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "text/event-stream"},
        "chunks": [b"chunk1", b"chunk2", b"chunk3"],
    }


class CapturingTracer(AbstractTracer):
    """Tracer that captures all logged traces for testing."""

    def __init__(self):
        self.traces: list[HTTPTrace] = []

    def log(self, trace: HTTPTrace) -> None:
        """Capture the trace."""
        self.traces.append(trace)

    def clear(self):
        """Clear captured traces."""
        self.traces.clear()


@pytest.fixture
def capturing_tracer():
    """Create a capturing tracer instance."""
    return CapturingTracer()


@pytest.fixture(autouse=True)
def setup_test_filter():
    """Set up URL filter for tests to allow test URLs."""
    # Create a filter that allows test URLs
    test_filter = URLFilter(
        allow_urls=["https://api.example.com/*"],
        extend_defaults=True,
    )
    set_global_filter(test_filter)
    yield
    # Reset to default filter after test
    set_global_filter(None)


@pytest.fixture
def mock_http_server(monkeypatch):
    """Mock HTTP server responses."""
    responses = {}

    def add_response(
        url: str, method: str, status: int, body: bytes, headers: dict = None,
    ):
        key = f"{method.upper()}:{url}"
        responses[key] = {
            "status": status,
            "body": body,
            "headers": headers or {},
        }

    return type(
        "MockServer",
        (),
        {
            "add_response": add_response,
            "responses": responses,
        },
    )()
