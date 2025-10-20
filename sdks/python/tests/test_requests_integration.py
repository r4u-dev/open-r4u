"""Tests for requests HTTP client integration."""

import requests
from unittest.mock import Mock

from r4u.integrations.http import trace_requests_session, trace_requests, PrintTracer, RequestInfo


class TestRequestsIntegration:
    """Test requests integration functionality."""

    def test_trace_session_basic(self):
        """Test basic session tracing functionality."""
        session = requests.Session()
        mock_tracer = Mock()
        
        # Store original send method
        original_send = session.send
        
        trace_requests_session(session, mock_tracer)
        
        # Verify the send method was wrapped
        assert hasattr(session, 'send')
        assert session.send != original_send

    def test_trace_session_integration(self):
        """Test session tracing integration with real HTTP requests."""
        session = requests.Session()
        mock_tracer = Mock()
        
        trace_requests_session(session, mock_tracer)
        
        # Make a real request to httpbin.org (which should work)
        try:
            session.get('https://httpbin.org/get', timeout=5)
            # Verify tracer was called
            mock_tracer.trace_request.assert_called_once()
            
            # Verify the request info structure
            call_args = mock_tracer.trace_request.call_args[0][0]
            assert isinstance(call_args, RequestInfo)
            assert call_args.method == 'GET'
            assert 'httpbin.org' in call_args.url
            assert call_args.status_code == 200
            assert call_args.error is None
            
        except requests.RequestException:
            # If the request fails, that's also fine for testing
            # Just verify the tracer was called
            mock_tracer.trace_request.assert_called_once()
            
            call_args = mock_tracer.trace_request.call_args[0][0]
            assert isinstance(call_args, RequestInfo)
            assert call_args.method == 'GET'
            assert 'httpbin.org' in call_args.url

    def test_trace_requests_global(self):
        """Test global requests module tracing."""
        mock_tracer = Mock()
        
        # Store original methods
        original_get = requests.get
        original_post = requests.post
        
        try:
            trace_requests(mock_tracer)
            
            # Verify methods were patched
            assert requests.get != original_get
            assert requests.post != original_post
            
        finally:
            # Restore original methods
            requests.get = original_get
            requests.post = original_post

    def test_print_tracer(self):
        """Test the PrintTracer implementation."""
        tracer = PrintTracer()
        
        # Create a mock request info
        request_info = RequestInfo(
            method='GET',
            url='https://example.com/test',
            status_code=200,
            request_payload=b'{"test": "data"}',
            response_payload=b'{"success": true}',
            started_at=None,
            completed_at=None
        )
        
        # This should not raise an exception
        tracer.trace_request(request_info)

    def test_request_info_structure(self):
        """Test RequestInfo dataclass structure."""
        request_info = RequestInfo(
            method='POST',
            url='https://api.example.com/data',
            headers={'Content-Type': 'application/json'},
            request_payload=b'{"key": "value"}',
            status_code=201,
            response_payload=b'{"id": 123}',
            error=None
        )
        
        assert request_info.method == 'POST'
        assert request_info.url == 'https://api.example.com/data'
        assert request_info.headers == {'Content-Type': 'application/json'}
        assert request_info.request_payload == b'{"key": "value"}'
        assert request_info.status_code == 201
        assert request_info.response_payload == b'{"id": 123}'
        assert request_info.error is None

    def test_request_info_defaults(self):
        """Test RequestInfo default values."""
        request_info = RequestInfo(
            method='GET',
            url='https://example.com'
        )
        
        assert request_info.headers == {}
        assert request_info.request_payload is None
        assert request_info.status_code is None
        assert request_info.response_payload is None
        assert request_info.error is None
