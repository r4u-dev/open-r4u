"""Tests for LangChain integration."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from r4u.integrations.langchain import wrap_langchain, R4UCallbackHandler, LANGCHAIN_AVAILABLE
from r4u.client import R4UClient


# Skip all tests if LangChain is not available
pytestmark = pytest.mark.skipif(
    not LANGCHAIN_AVAILABLE,
    reason="LangChain is not installed"
)


class TestR4UCallbackHandler:
    """Test R4UCallbackHandler class."""

    @pytest.fixture
    def mock_r4u_client(self):
        """Create a mock R4U client."""
        client = Mock(spec=R4UClient)
        client.create_trace = Mock()
        client.create_trace_async = Mock()
        return client

    @pytest.fixture
    def handler(self, mock_r4u_client):
        """Create a callback handler with mock client."""
        return R4UCallbackHandler(mock_r4u_client)

    def test_on_llm_start(self, handler, mock_r4u_client):
        """Test on_llm_start callback."""
        serialized = {"name": "test-model"}
        prompts = ["What is the capital of France?"]
        
        handler.on_llm_start(serialized, prompts)
        
        assert handler._current_trace["model"] == "test-model"
        assert len(handler._current_trace["messages"]) == 1
        assert handler._current_trace["messages"][0]["role"] == "user"
        assert handler._current_trace["messages"][0]["content"] == prompts[0]
        assert handler._call_path is not None

    def test_on_chat_model_start(self, handler, mock_r4u_client):
        """Test on_chat_model_start callback."""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        serialized = {"id": ["langchain", "chat_models", "openai", "ChatOpenAI"]}
        messages = [
            [
                SystemMessage(content="You are helpful"),
                HumanMessage(content="Hello"),
            ]
        ]
        
        handler.on_chat_model_start(serialized, messages)
        
        assert handler._current_trace["model"] == "ChatOpenAI"
        assert len(handler._current_trace["messages"]) == 2
        assert handler._current_trace["messages"][0]["role"] == "system"
        assert handler._current_trace["messages"][0]["content"] == "You are helpful"
        assert handler._current_trace["messages"][1]["role"] == "user"
        assert handler._current_trace["messages"][1]["content"] == "Hello"

    def test_on_llm_end_with_chat_message(self, handler, mock_r4u_client):
        """Test on_llm_end callback with chat message response."""
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import LLMResult, ChatGeneration
        
        # Setup initial trace
        handler._current_trace = {
            "started_at": datetime.utcnow(),
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "tools": None,
        }
        handler._call_path = "test_file.py::test_function"
        
        # Create mock response
        message = AIMessage(content="Hi there!")
        generation = ChatGeneration(message=message)
        response = LLMResult(generations=[[generation]])
        
        handler.on_llm_end(response)
        
        # Verify trace was created
        mock_r4u_client.create_trace.assert_called_once()
        call_kwargs = mock_r4u_client.create_trace.call_args[1]
        
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        # Only input messages, not the assistant response
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["result"] == "Hi there!"
        assert call_kwargs["error"] is None
        assert call_kwargs["path"] == "test_file.py::test_function"

    def test_on_llm_end_with_tool_calls(self, handler, mock_r4u_client):
        """Test on_llm_end with tool calls in response."""
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import LLMResult, ChatGeneration
        
        # Setup initial trace
        handler._current_trace = {
            "started_at": datetime.utcnow(),
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "What's the weather?"}
            ],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object"},
                }
            ],
        }
        handler._call_path = "test_file.py::test_function"
        
        # Create mock response with tool calls
        tool_call = {
            "id": "call_123",
            "name": "get_weather",
            "args": {"location": "Paris"}
        }
        message = AIMessage(
            content="",
            tool_calls=[tool_call]
        )
        generation = ChatGeneration(message=message)
        response = LLMResult(generations=[[generation]])
        
        handler.on_llm_end(response)
        
        # Verify trace was created
        # Note: Assistant response with tool calls is in result field, not messages
        mock_r4u_client.create_trace.assert_called_once()
        call_kwargs = mock_r4u_client.create_trace.call_args[1]
        
        # Only input messages
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        # Result is None for tool calls (no text content)
        assert call_kwargs["result"] is None

    def test_on_llm_error(self, handler, mock_r4u_client):
        """Test on_llm_error callback."""
        handler._current_trace = {
            "started_at": datetime.utcnow(),
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": None,
        }
        handler._call_path = "test_file.py::test_function"
        
        error = Exception("API Error")
        handler.on_llm_error(error)
        
        # Verify trace was created with error
        mock_r4u_client.create_trace.assert_called_once()
        call_kwargs = mock_r4u_client.create_trace.call_args[1]
        
        assert call_kwargs["error"] == "API Error"
        assert call_kwargs["result"] is None

    def test_extract_model_name_from_invocation_params(self, handler):
        """Test model name extraction from invocation params."""
        serialized = {}
        kwargs = {
            "invocation_params": {
                "model": "gpt-4"
            }
        }
        
        model = handler._extract_model_name(serialized, kwargs)
        assert model == "gpt-4"

    def test_extract_model_name_from_serialized_id(self, handler):
        """Test model name extraction from serialized id."""
        serialized = {
            "id": ["langchain", "chat_models", "openai", "ChatOpenAI"]
        }
        kwargs = {}
        
        model = handler._extract_model_name(serialized, kwargs)
        assert model == "ChatOpenAI"

    def test_normalize_message_with_content(self, handler):
        """Test message normalization."""
        from langchain_core.messages import HumanMessage
        
        message = HumanMessage(content="Hello world")
        normalized = handler._normalize_langchain_message(message)
        
        assert normalized["role"] == "user"
        assert normalized["content"] == "Hello world"

    def test_normalize_message_with_tool_calls(self, handler):
        """Test normalizing message with tool calls."""
        from langchain_core.messages import AIMessage
        
        tool_call = {
            "id": "call_123",
            "name": "get_weather",
            "args": {"location": "Paris"}
        }
        message = AIMessage(content="", tool_calls=[tool_call])
        normalized = handler._normalize_langchain_message(message)
        
        assert normalized["role"] == "assistant"
        assert "tool_calls" in normalized
        assert len(normalized["tool_calls"]) == 1
        assert normalized["tool_calls"][0]["function"]["name"] == "get_weather"

    def test_normalize_message_with_additional_kwargs(self, handler):
        """Test normalizing message with additional_kwargs (function_call)."""
        from langchain_core.messages import AIMessage
        
        message = AIMessage(
            content="",
            additional_kwargs={
                "function_call": {
                    "name": "get_weather",
                    "arguments": '{"location": "Paris"}'
                }
            }
        )
        normalized = handler._normalize_langchain_message(message)
        
        assert "tool_calls" in normalized
        assert len(normalized["tool_calls"]) == 1
        assert normalized["tool_calls"][0]["function"]["name"] == "get_weather"
        assert normalized["tool_calls"][0]["function"]["arguments"]["location"] == "Paris"

    def test_parse_json_safe(self, handler):
        """Test safe JSON parsing."""
        # Valid JSON
        result = handler._parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}
        
        # Invalid JSON - should return original
        result = handler._parse_json_safe("not json")
        assert result == "not json"
        
        # Non-string - should return as-is
        result = handler._parse_json_safe({"key": "value"})
        assert result == {"key": "value"}

    def test_extract_tools(self, handler):
        """Test tool extraction from invocation params."""
        invocation_params = {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the weather",
                        "parameters": {"type": "object"}
                    }
                }
            ]
        }
        
        tools = handler._extract_tools(invocation_params)
        
        assert tools is not None
        assert len(tools) == 1
        assert tools[0]["name"] == "get_weather"
        assert tools[0]["description"] == "Get the weather"


class TestWrapLangChain:
    """Test wrap_langchain function."""

    def test_wrap_langchain_creates_handler(self):
        """Test that wrap_langchain creates a handler."""
        handler = wrap_langchain(api_url="http://test:8000", timeout=10.0)
        
        assert isinstance(handler, R4UCallbackHandler)
        assert handler._r4u_client.api_url == "http://test:8000"
        assert handler._r4u_client.timeout == 10.0

    def test_wrap_langchain_default_params(self):
        """Test wrap_langchain with default parameters."""
        handler = wrap_langchain()
        
        assert isinstance(handler, R4UCallbackHandler)
        assert handler._r4u_client.api_url == "http://localhost:8000"
        assert handler._r4u_client.timeout == 30.0


@pytest.mark.integration
class TestLangChainIntegrationE2E:
    """End-to-end integration tests with LangChain."""

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI for testing."""
        with patch("langchain_openai.ChatOpenAI") as mock:
            yield mock

    def test_basic_chat_completion(self, mock_openai):
        """Test basic chat completion tracing."""
        from langchain_core.messages import AIMessage, HumanMessage
        from langchain_core.outputs import LLMResult, ChatGeneration
        
        # Create handler
        handler = wrap_langchain(api_url="http://test:8000")
        
        # Mock the client's create_trace
        handler._r4u_client.create_trace = Mock()
        
        # Simulate LangChain callbacks with real message
        serialized = {"id": ["langchain", "chat_models", "openai", "ChatOpenAI"]}
        messages = [[HumanMessage(content="Hello")]]
        
        handler.on_chat_model_start(serialized, messages, invocation_params={"model": "gpt-3.5-turbo"})
        
        # Simulate response
        response_msg = AIMessage(content="Hi there!")
        generation = ChatGeneration(message=response_msg)
        result = LLMResult(generations=[[generation]])
        
        handler.on_llm_end(result)
        
        # Verify trace was created
        handler._r4u_client.create_trace.assert_called_once()
        call_kwargs = handler._r4u_client.create_trace.call_args[1]
        
        assert call_kwargs["model"] == "gpt-3.5-turbo"
        # Only input message
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["result"] == "Hi there!"

    def test_conversation_with_memory(self, mock_openai):
        """Test conversation with message history."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        from langchain_core.outputs import LLMResult, ChatGeneration
        
        handler = wrap_langchain(api_url="http://test:8000")
        handler._r4u_client.create_trace = Mock()
        
        # Simulate a conversation with history
        serialized = {"id": ["langchain", "chat_models", "openai", "ChatOpenAI"]}
        messages = [[
            SystemMessage(content="You are helpful"),
            HumanMessage(content="My name is Alice"),
            AIMessage(content="Nice to meet you Alice!"),
            HumanMessage(content="What's my name?"),
        ]]
        
        handler.on_chat_model_start(
            serialized,
            messages,
            invocation_params={"model": "gpt-3.5-turbo"}
        )
        
        # Simulate response
        response_msg = AIMessage(content="Your name is Alice")
        generation = ChatGeneration(message=response_msg)
        result = LLMResult(generations=[[generation]])
        
        handler.on_llm_end(result)
        
        # Verify all input messages were captured (not the response)
        call_kwargs = handler._r4u_client.create_trace.call_args[1]
        assert len(call_kwargs["messages"]) == 4  # Input history only
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert call_kwargs["messages"][2]["role"] == "assistant"
        assert call_kwargs["messages"][3]["role"] == "user"
        # Response is in result field
        assert call_kwargs["result"] == "Your name is Alice"
