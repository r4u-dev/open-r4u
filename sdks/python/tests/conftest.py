"""Test configuration for R4U SDK."""

import pytest
from unittest.mock import Mock
from r4u.client import R4UClient

@pytest.fixture
def mock_r4u_client():
    """Create a mock R4U client."""
    return Mock(spec=R4UClient)

@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    
    # Mock the response structure
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "Test response"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Mock the completions create method
    mock_client.chat.completions.create.return_value = mock_response
    mock_client.chat.completions.acreate.return_value = mock_response
    
    return mock_client