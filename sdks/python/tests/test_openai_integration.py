"""Tests for OpenAI integration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from r4u.tracing.openai import wrap_openai, OpenAIWrapper


class TestOpenAIIntegration:
    """Test cases for OpenAI integration."""

    def test_wrap_openai_returns_wrapper(self):
        """Test that wrap_openai returns an OpenAIWrapper."""
        mock_client = Mock()
        mock_client.chat.completions = Mock()
        
        wrapped = wrap_openai(mock_client)
        assert isinstance(wrapped, OpenAIWrapper)

    def test_wrapper_delegates_attributes(self):
        """Test that wrapper delegates attributes to original client."""
        mock_client = Mock()
        mock_client.some_attribute = "test_value"
        mock_client.chat.completions = Mock()
        
        wrapped = wrap_openai(mock_client)
        assert wrapped.some_attribute == "test_value"

    @patch('r4u.tracing.openai.R4UClient')
    def test_create_completion_with_tracing(self, mock_r4u_client_class):
        """Test that completion calls create traces."""
        # Setup mocks
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Hello there!"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Wrap client and make call
        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        messages = [{"role": "user", "content": "Hello"}]
        result = wrapped.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        
        # Verify original method was called
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        
        # Verify trace was created
        mock_r4u_client.create_trace.assert_called_once()
        call_args = mock_r4u_client.create_trace.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        # Only input messages, not the response
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == "Hello"
        assert call_args["messages"][0]["role"] == "user"
        assert call_args.get("tools") is None
        # Response is in result field
        assert call_args["result"] == "Hello there!"
        assert "started_at" in call_args
        assert "completed_at" in call_args
        
        # Verify path includes method name
        assert "path" in call_args
        assert call_args["path"] is not None
        assert "create" in call_args["path"], "Path should include the 'create' method name"
        
        # Verify result is returned
        assert result == mock_response
        assert messages == [{"role": "user", "content": "Hello"}]

    @patch('r4u.tracing.openai.R4UClient')
    def test_create_completion_with_error_tracing(self, mock_r4u_client_class):
        """Test that errors are traced when completion fails."""
        # Setup mocks
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Wrap client and make call
        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        
        with pytest.raises(Exception, match="API Error"):
            wrapped.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        # Verify trace was created with error
        mock_r4u_client.create_trace.assert_called_once()
        call_args = mock_r4u_client.create_trace.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        # Only input messages
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0] == {"role": "user", "content": "Hello"}
        assert call_args["error"] == "API Error"
        assert call_args.get("result") is None

    @pytest.mark.asyncio
    @patch('r4u.tracing.openai.R4UClient')
    async def test_async_create_completion_with_tracing(self, mock_r4u_client_class):
        """Test that async completion calls create traces."""
        # Setup mocks
        mock_r4u_client = Mock()
        mock_r4u_client.create_trace_async = AsyncMock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Hello there!"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # Create async mock for the create method (which is what acreate calls now)
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Wrap client and make call
        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        messages = [{"role": "user", "content": "Hello"}]
        result = await wrapped.chat.completions.acreate(
            model="gpt-3.5-turbo",
            messages=messages
        )

        # Verify original method was called
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        # Verify async trace was created
        mock_r4u_client.create_trace_async.assert_called_once()
        call_args = mock_r4u_client.create_trace_async.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        # Only input messages, not the response
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == "Hello"
        assert call_args["messages"][0]["role"] == "user"
        assert call_args.get("tools") is None
        # Response is in result field
        assert call_args["result"] == "Hello there!"

        # Verify path includes method name for async calls
        assert "path" in call_args
        assert call_args["path"] is not None
        assert "acreate" in call_args["path"], "Path should include the 'acreate' method name"

        # Verify result is returned
        assert result == mock_response
        assert messages == [{"role": "user", "content": "Hello"}]

    @patch('r4u.tracing.openai.R4UClient')
    def test_tool_calls_are_traced(self, mock_r4u_client_class):
        """Ensure tool definitions and tool calls are captured in traces."""
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client

        mock_openai_client = Mock()
        tool_call_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "lookup_user",
                        "arguments": '{"user_id": "42"}'
                    },
                }
            ],
        }
        mock_choice = Mock()
        mock_choice.message = tool_call_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        request_messages = [{"role": "user", "content": "Find user 42"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "lookup_user",
                    "description": "Lookup a user by id",
                    "parameters": {
                        "type": "object",
                        "properties": {"user_id": {"type": "string"}},
                    },
                },
            }
        ]

        wrapped.chat.completions.create(
            model="gpt-4.1",
            messages=request_messages,
            tools=tools,
        )

        mock_r4u_client.create_trace.assert_called_once()
        call_args = mock_r4u_client.create_trace.call_args[1]

        # Only input messages (not the assistant response)
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "Find user 42"
        
        # Result should be None for tool calls (no text content)
        assert call_args.get("result") is None

        # Tool definitions should be captured
        tool_definitions = call_args["tools"]
        assert len(tool_definitions) == 1
        assert tool_definitions[0]["name"] == "lookup_user"
        assert tool_definitions[0]["type"] == "function"

        # Ensure request payload was not mutated
        assert request_messages == [{"role": "user", "content": "Find user 42"}]
        assert tools[0]["function"]["name"] == "lookup_user"

    @patch('r4u.tracing.openai.R4UClient')
    def test_trace_creation_failure_doesnt_break_request(self, mock_r4u_client_class):
        """Test that trace creation failures don't break the original request."""
        # Setup mocks
        mock_r4u_client = Mock()
        mock_r4u_client.create_trace.side_effect = Exception("Trace API down")
        mock_r4u_client_class.return_value = mock_r4u_client
        
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Hello there!"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Wrap client and make call
        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        
        # Should not raise exception even though tracing fails
        result = wrapped.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Verify original method was called and result returned
        mock_openai_client.chat.completions.create.assert_called_once()
        assert result == mock_response
        
        # Verify trace creation was attempted
        mock_r4u_client.create_trace.assert_called_once()

    @patch('r4u.tracing.openai.R4UClient')
    def test_path_includes_method_name(self, mock_r4u_client_class):
        """Test that the call path includes the method name (create)."""
        # Setup mocks
        mock_r4u_client = Mock()
        mock_r4u_client_class.return_value = mock_r4u_client
        
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Test response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Wrap client and make call
        wrapped = wrap_openai(mock_openai_client)
        assert wrapped.chat is not None
        wrapped.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}]
        )
        
        # Verify trace was created with path including method name
        mock_r4u_client.create_trace.assert_called_once()
        call_args = mock_r4u_client.create_trace.call_args[1]
        
        # Check path contains method name
        path = call_args["path"]
        assert path is not None, "Path should not be None"
        assert "create" in path, f"Path '{path}' should include 'create' method name"
        assert "test_openai_integration.py" in path, "Path should include test file name"
        assert "test_path_includes_method_name" in path, "Path should include test function name"
        
        # Verify format is correct (file::function->...->method)
        assert "::" in path, "Path should have :: separator"
        assert "->" in path, "Path should have -> separators for call chain"