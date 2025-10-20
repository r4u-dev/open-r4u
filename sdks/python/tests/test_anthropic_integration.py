"""Tests for Anthropic integration."""

from unittest.mock import Mock, patch
from r4u.integrations.anthropic import AnthropicWrapper, MessagesWrapper, wrap_anthropic


def test_anthropic_wrapper_initialization():
    """Test that AnthropicWrapper initializes correctly."""
    mock_client = Mock()
    mock_r4u_client = Mock()
    project = "test-project"
    
    wrapper = AnthropicWrapper(mock_client, mock_r4u_client, project)
    
    assert wrapper._original_client == mock_client
    assert wrapper._r4u_client == mock_r4u_client
    assert wrapper._project == project


def test_messages_wrapper_initialization():
    """Test that MessagesWrapper initializes correctly."""
    mock_messages_client = Mock()
    mock_r4u_client = Mock()
    project = "test-project"
    
    wrapper = MessagesWrapper(mock_messages_client, mock_r4u_client, project)
    
    assert wrapper._original_messages == mock_messages_client
    assert wrapper._r4u_client == mock_r4u_client
    assert wrapper._project == project


def test_wrap_anthropic():
    """Test that wrap_anthropic creates a wrapper correctly."""
    mock_client = Mock()
    
    with patch('r4u.integrations.anthropic.R4UClient') as mock_r4u_client_class:
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        wrapped = wrap_anthropic(mock_client, project="test-project")
        
        assert isinstance(wrapped, AnthropicWrapper)
        assert wrapped._original_client == mock_client
        assert wrapped._project == "test-project"


def test_wrap_anthropic_with_env_project():
    """Test that wrap_anthropic uses environment variable for project."""
    mock_client = Mock()
    
    with patch('r4u.integrations.anthropic.R4UClient') as mock_r4u_client_class, \
         patch.dict('os.environ', {'R4U_PROJECT': 'env-project'}):
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        wrapped = wrap_anthropic(mock_client)
        
        assert wrapped._project == "env-project"


def test_wrap_anthropic_default_project():
    """Test that wrap_anthropic uses default project when none specified."""
    mock_client = Mock()
    
    with patch('r4u.integrations.anthropic.R4UClient') as mock_r4u_client_class, \
         patch.dict('os.environ', {}, clear=True):
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        wrapped = wrap_anthropic(mock_client)
        
        assert wrapped._project == "Default Project"


def test_to_plain_method():
    """Test the _to_plain method handles different data types."""
    # Test with dict
    result = MessagesWrapper._to_plain({"key": "value"})
    assert result == {"key": "value"}
    
    # Test with list
    result = MessagesWrapper._to_plain([1, 2, 3])
    assert result == [1, 2, 3]
    
    # Test with string
    result = MessagesWrapper._to_plain("test")
    assert result == "test"


def test_normalize_message():
    """Test message normalization."""
    message = {
        "role": "user",
        "content": "Hello"
    }
    
    result = MessagesWrapper._normalize_message(message)
    assert result == {"role": "user", "content": "Hello"}


def test_extract_tool_definitions():
    """Test tool definitions extraction."""
    kwargs = {
        "tools": [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {"type": "object"}
            }
        ]
    }
    
    result = MessagesWrapper._extract_tool_definitions(kwargs)
    assert result == [
        {
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {"type": "object"}
        }
    ]


def test_extract_tool_definitions_empty():
    """Test tool definitions extraction with no tools."""
    kwargs = {}
    
    result = MessagesWrapper._extract_tool_definitions(kwargs)
    assert result is None


def test_extract_response_content():
    """Test response content extraction."""
    # Test with list of content blocks
    result = Mock()
    result.content = [{"type": "text", "text": "Hello world"}]
    
    content = MessagesWrapper._extract_response_content(result)
    assert content == "Hello world"
    
    # Test with single text content
    result = Mock()
    result.content = "Hello world"
    
    content = MessagesWrapper._extract_response_content(result)
    assert content == "Hello world"


def test_extract_response_content_none():
    """Test response content extraction with no content."""
    result = Mock()
    result.content = None
    
    content = MessagesWrapper._extract_response_content(result)
    assert content is None


def test_extract_token_usage():
    """Test token usage extraction."""
    usage = Mock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    
    result = Mock()
    result.usage = usage
    
    input_tokens, output_tokens, total_tokens = MessagesWrapper._extract_token_usage(result)
    assert input_tokens == 10
    assert output_tokens == 5
    assert total_tokens == 15


def test_extract_token_usage_none():
    """Test token usage extraction with no usage."""
    result = Mock()
    result.usage = None
    
    input_tokens, output_tokens, total_tokens = MessagesWrapper._extract_token_usage(result)
    assert input_tokens is None
    assert output_tokens is None
    assert total_tokens is None
