"""Tests for credential redaction."""

import pytest
from unittest.mock import Mock
from r4u.utils import redact_headers, SENSITIVE_HEADERS
from r4u.tracing.http.requests import _build_trace_context as requests_build_context
from r4u.tracing.http.httpx import _build_trace_context as httpx_build_context
from r4u.tracing.http.aiohttp import _create_async_wrapper
import requests
import httpx
from datetime import datetime, timezone

class TestRedactionUtils:
    """Test the redact_headers utility function."""

    def test_redact_sensitive_headers(self):
        """Test that sensitive headers are redacted."""
        headers = {
            "Authorization": "Bearer secret-token",
            "X-API-Key": "12345",
            "Content-Type": "application/json",
            "User-Agent": "test-agent",
        }
        
        redacted = redact_headers(headers)
        
        assert redacted["Authorization"] == "[REDACTED]"
        assert redacted["X-API-Key"] == "[REDACTED]"
        assert redacted["Content-Type"] == "application/json"
        assert redacted["User-Agent"] == "test-agent"

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        headers = {
            "authorization": "secret",
            "API-KEY": "secret",
            "Token": "secret",
        }
        
        redacted = redact_headers(headers)
        
        for key in headers:
            assert redacted[key] == "[REDACTED]"

    def test_empty_headers(self):
        """Test with empty headers."""
        assert redact_headers({}) == {}

    def test_no_sensitive_headers(self):
        """Test with no sensitive headers."""
        headers = {"Content-Type": "application/json"}
        assert redact_headers(headers) == headers


class TestRequestsRedaction:
    """Test redaction in requests wrapper."""

    def test_requests_headers_redaction(self):
        """Test that requests headers are redacted in trace context."""
        request = Mock(spec=requests.PreparedRequest)
        request.method = "GET"
        request.url = "https://api.example.com"
        request.headers = {
            "Authorization": "Bearer secret",
            "Content-Type": "application/json"
        }
        request.body = None

        ctx = requests_build_context(request)
        
        assert ctx["request_headers"]["Authorization"] == "[REDACTED]"
        assert ctx["request_headers"]["Content-Type"] == "application/json"


class TestHttpxRedaction:
    """Test redaction in httpx wrapper."""

    def test_httpx_headers_redaction(self):
        """Test that httpx headers are redacted in trace context."""
        request = Mock(spec=httpx.Request)
        request.method = "GET"
        request.url = httpx.URL("https://api.example.com")
        request.headers = httpx.Headers({
            "Authorization": "Bearer secret",
            "Content-Type": "application/json"
        })
        request.content = b""

        # httpx normalizes headers to lowercase when converting to dict
        ctx = httpx_build_context(request)
        assert ctx["request_headers"]["authorization"] == "[REDACTED]"
        assert ctx["request_headers"]["content-type"] == "application/json"
