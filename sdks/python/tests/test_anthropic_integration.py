"""Tests for Anthropic integration."""

from unittest.mock import Mock, patch
from r4u.tracing.anthropic import Anthropic, AsyncAnthropic


def test_anthropic_initialization():
    """Test that Anthropic class initializes correctly."""
    with patch('r4u.tracing.anthropic.trace_client') as mock_trace_client, \
         patch('r4u.tracing.anthropic.get_r4u_client') as mock_get_client:

        mock_r4u_client = Mock()
        mock_get_client.return_value = mock_r4u_client

        Anthropic()

        # Verify that trace_client was called with the httpx client and tracer
        mock_trace_client.assert_called_once()
        assert len(mock_trace_client.call_args[0]) == 2  # client and tracer


def test_async_anthropic_initialization():
    """Test that AsyncAnthropic class initializes correctly."""
    with patch('r4u.tracing.anthropic.trace_async_client') as mock_trace_client, \
         patch('r4u.tracing.anthropic.get_r4u_client') as mock_get_client:

        mock_r4u_client = Mock()
        mock_get_client.return_value = mock_r4u_client

        AsyncAnthropic()

        # Verify that trace_async_client was called with the httpx client and tracer
        mock_trace_client.assert_called_once()
        assert len(mock_trace_client.call_args[0]) == 2  # client and tracer


def test_anthropic_with_api_key():
    """Test that Anthropic can be initialized with an API key."""
    with patch('r4u.tracing.anthropic.trace_client') as mock_trace_client, \
         patch('r4u.tracing.anthropic.get_r4u_client') as mock_get_client:

        mock_r4u_client = Mock()
        mock_get_client.return_value = mock_r4u_client

        Anthropic(api_key="test-key")

        # Verify that trace_client was called
        mock_trace_client.assert_called_once()


def test_async_anthropic_with_api_key():
    """Test that AsyncAnthropic can be initialized with an API key."""
    with patch('r4u.tracing.anthropic.trace_async_client') as mock_trace_client, \
         patch('r4u.tracing.anthropic.get_r4u_client') as mock_get_client:

        mock_r4u_client = Mock()
        mock_get_client.return_value = mock_r4u_client

        AsyncAnthropic(api_key="test-key")

        # Verify that trace_async_client was called
        mock_trace_client.assert_called_once()
