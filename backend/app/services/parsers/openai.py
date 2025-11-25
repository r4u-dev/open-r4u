"""OpenAI API parser."""

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enums import FinishReason, MessageRole
from app.schemas.traces import (
    FunctionCallItem,
    FunctionToolCallItem,
    InputItem,
    MessageItem,
    OutputItem,
    OutputMessageContent,
    OutputMessageItem,
    Reasoning,
    ToolDefinition,
    ToolResultItem,
    TraceCreate,
)
from app.services.parsers.base import ProviderParser


class OpenAIParser(ProviderParser):
    """Parser for OpenAI API format."""

    def can_parse(self, url: str) -> bool:
        """Check if URL is an OpenAI endpoint."""
        parsed = urlparse(url)
        return "openai.com" in parsed.netloc or "api.openai.com" in parsed.netloc

    def _is_responses_api(self, request_body: dict[str, Any]) -> bool:
        """Check if this is the new Responses API format.

        The Responses API uses 'input' instead of 'messages' and has a different structure.
        """
        return "input" in request_body and "messages" not in request_body

    def _parse_sse_stream(self, streaming_response: str) -> list[dict[str, Any]]:
        """Parse Server-Sent Events (SSE) stream into list of events.

        Args:
            streaming_response: Raw SSE response with chunks concatenated by \n\n

        Returns:
            List of parsed event dictionaries

        """
        events = []
        lines = streaming_response.strip().split("\n")

        current_event = {}
        for line in lines:
            line = line.strip()

            if not line:
                # Empty line signals end of event
                if current_event:
                    events.append(current_event)
                    current_event = {}
                continue

            if line.startswith("event:"):
                current_event["event"] = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    current_event["done"] = True
                else:
                    try:
                        current_event["data"] = json.loads(data_str)
                    except json.JSONDecodeError:
                        # Skip invalid JSON
                        pass

        # Add last event if exists
        if current_event:
            events.append(current_event)

        return events

    def _reconstruct_chat_completions_from_stream(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Reconstruct a complete Chat Completions response from streaming chunks.

        Args:
            events: List of SSE events

        Returns:
            Reconstructed response body dictionary

        """
        # Initialize response structure
        response = {
            "id": None,
            "object": "chat.completion",
            "created": None,
            "model": None,
            "choices": [],
            "usage": None,
        }

        # Track content accumulation
        content_parts = []
        finish_reason = None

        for event in events:
            if event.get("done"):
                continue

            data = event.get("data")
            if not data:
                continue

            # Extract metadata from first chunk
            if response["id"] is None:
                response["id"] = data.get("id")
                response["created"] = data.get("created")
                response["model"] = data.get("model")
                response["system_fingerprint"] = data.get("system_fingerprint")
                response["service_tier"] = data.get("service_tier")

            # Process choices
            choices = data.get("choices", [])
            for choice in choices:
                delta = choice.get("delta", {})

                # Accumulate content
                if delta.get("content"):
                    content_parts.append(delta["content"])

                # Capture finish reason
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]

            # Extract usage from chunk (usually in the last chunk)
            if data.get("usage"):
                response["usage"] = data["usage"]

        # Build final choice
        if content_parts or finish_reason:
            response["choices"] = [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "".join(content_parts) if content_parts else None,
                    },
                    "finish_reason": finish_reason,
                },
            ]

        return response

    def _reconstruct_responses_api_from_stream(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Reconstruct a complete Responses API response from streaming events.

        Args:
            events: List of SSE events

        Returns:
            Reconstructed response body dictionary

        """
        # Initialize response structure
        response = {
            "id": None,
            "object": "response",
            "created": None,
            "model": None,
            "output": None,
            "finish_reason": None,
            "usage": None,
        }

        # Track the final completed event
        for event in events:
            event_type = event.get("event")
            data = event.get("data")

            if not data:
                continue

            # Look for response.completed event which has everything
            if (
                event_type == "response.completed"
                or data.get("type") == "response.completed"
            ):
                response_data = data.get("response", data)
                response["id"] = response_data.get("id")
                response["created"] = response_data.get(
                    "created_at",
                ) or response_data.get("created")
                response["model"] = response_data.get("model")
                response["finish_reason"] = response_data.get("finish_reason")
                response["usage"] = response_data.get("usage")
                response["system_fingerprint"] = response_data.get("system_fingerprint")
                response["service_tier"] = response_data.get("service_tier")
                response["temperature"] = response_data.get("temperature")

                # Extract output text from output items
                output_items = response_data.get("output", [])
                if output_items:
                    if isinstance(output_items, list):
                        # Extract text from message content
                        for item in output_items:
                            if item.get("type") == "message":
                                content = item.get("content", [])
                                if content:
                                    for content_part in content:
                                        if content_part.get("type") == "output_text":
                                            response["output"] = content_part.get(
                                                "text",
                                            )
                                            break
                                if response["output"]:
                                    break
                break

            # Fallback: look for output_text.done event
            if (
                event_type == "response.output_text.done"
                or data.get("type") == "response.output_text.done"
            ):
                if not response["output"]:
                    response["output"] = data.get("text")

        return response

    def parse(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
        is_streaming: bool = False,
        streaming_response: str | None = None,
    ) -> TraceCreate:
        """Parse OpenAI API request/response.

        Supports both Chat Completions API and the new Responses API.
        Also handles streaming responses.
        """
        # Handle streaming responses
        if is_streaming and streaming_response:
            events = self._parse_sse_stream(streaming_response)

            # Reconstruct response based on API type
            if self._is_responses_api(request_body):
                response_body = self._reconstruct_responses_api_from_stream(events)
            else:
                response_body = self._reconstruct_chat_completions_from_stream(events)

        # Check if this is the new Responses API
        if self._is_responses_api(request_body):
            return self._parse_responses_api(
                request_body,
                response_body,
                started_at,
                completed_at,
                error,
                metadata,
                call_path,
            )

        # Otherwise parse as Chat Completions API (default)
        return self._parse_chat_completions_api(
            request_body,
            response_body,
            started_at,
            completed_at,
            error,
            metadata,
            call_path,
        )

    def _parse_chat_completions_api(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
    ) -> TraceCreate:
        """Parse Chat Completions API format."""
        # Extract model
        model = request_body.get("model", "unknown")

        # Extract messages from request
        messages = request_body.get("messages", [])
        input_items: list[InputItem] = []

        for msg in messages:
            role_str = msg.get("role", "user")

            # Handle tool result messages - create ToolResultItem
            if role_str == "tool":
                tool_call_id = msg.get("tool_call_id")
                name = msg.get("name")
                content = msg.get("content")
                if tool_call_id:
                    input_items.append(
                        ToolResultItem(
                            call_id=tool_call_id,
                            tool_name=name,
                            result=content,
                        ),
                    )
                continue

            try:
                role = MessageRole(role_str)
            except ValueError:
                role = MessageRole.USER

            if msg.get("content"):
                input_items.append(
                    MessageItem(
                        role=role,
                        content=msg.get("content"),
                    ),
                )
            elif msg.get("tool_calls"):
                # Handle tool calls in messages
                tool_calls_data = msg.get("tool_calls")
                for tc in tool_calls_data:
                    function_data = tc.get("function", {})
                    arguments_str = function_data.get("arguments", "")

                    input_items.append(
                        FunctionCallItem(
                            call_id=tc.get("id", ""),
                            name=function_data.get("name", ""),
                            arguments=arguments_str,
                        ),
                    )

        # Extract result from response
        result = None
        # Parse response
        finish_reason = None
        output_items: list[OutputItem] = []
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        cached_tokens = None
        reasoning_tokens = None
        system_fingerprint = None

        if not error and response_body:
            choices = response_body.get("choices", [])
            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content")

                # Create output message item if content exists
                if content:
                    output_items.append(
                        OutputMessageItem(
                            id=f"msg_{response_body.get('id', 'unknown')}",
                            content=[OutputMessageContent(type="text", text=content)],
                            status="completed",
                        ),
                    )

                # Handle tool calls from assistant response
                tool_calls_data = message.get("tool_calls")
                if tool_calls_data:
                    for tc in tool_calls_data:
                        function_data = tc.get("function", {})
                        arguments_str = function_data.get("arguments", "")

                        # Also add to output items
                        output_items.append(
                            FunctionToolCallItem(
                                id=tc.get("id", ""),
                                call_id=tc.get("id", ""),
                                name=function_data.get("name", ""),
                                arguments=arguments_str,
                                status="completed",
                            ),
                        )

                # Extract finish reason
                finish_reason_str = choice.get("finish_reason")
                if finish_reason_str:
                    try:
                        finish_reason = FinishReason(finish_reason_str)
                    except ValueError:
                        pass

            # Extract token usage
            usage = response_body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

            # Additional token metrics
            # Responses API uses input_tokens_details/output_tokens_details
            # Chat Completions API uses prompt_tokens_details/completion_tokens_details
            prompt_tokens_details = (
                usage.get("prompt_tokens_details")
                or usage.get("input_tokens_details")
                or {}
            )
            cached_tokens = prompt_tokens_details.get("cached_tokens")

            completion_tokens_details = (
                usage.get("completion_tokens_details")
                or usage.get("output_tokens_details")
                or {}
            )
            reasoning_tokens = completion_tokens_details.get("reasoning_tokens")

            system_fingerprint = response_body.get("system_fingerprint")

        # Extract tools from request
        tools = None
        tools_data = request_body.get("tools")
        if tools_data:
            tools = [
                ToolDefinition(
                    type=t.get("type", "function"),
                    function=t.get("function", {}),
                )
                for t in tools_data
            ]

        # Extract reasoning configuration
        reasoning = None
        reasoning_data = request_body.get("reasoning")
        if reasoning_data:
            reasoning = Reasoning(**reasoning_data)

        # Extract other request parameters
        instructions = request_body.get("instructions")
        temperature = request_body.get("temperature")
        tool_choice = request_body.get("tool_choice")
        response_format = request_body.get("response_format")

        # Extract project from metadata or use default
        project = (
            metadata.get("project", "Default Project")
            if metadata
            else "Default Project"
        )
        max_tokens = request_body.get("max_tokens")

        return TraceCreate(
            project=project,
            model=model,
            output=output_items,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=call_path,
            tools=tools,
            instructions=instructions,
            prompt=None,  # Not directly available in OpenAI format
            temperature=temperature,
            tool_choice=tool_choice,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            finish_reason=finish_reason,
            system_fingerprint=system_fingerprint,
            reasoning=reasoning,
            response_schema=response_format,
            trace_metadata=metadata,
            max_tokens=max_tokens,
        )

    def _parse_responses_api(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
    ) -> TraceCreate:
        """Parse new OpenAI Responses API format.

        The Responses API has a different structure:
        - Uses 'input' instead of 'messages'
        - Response has 'output' field
        - Different token usage structure
        """
        # Extract model
        model = request_body.get("model", "unknown")

        # Extract input items from request
        # In Responses API, 'input' can be a list of messages or a simpler format
        request_input = request_body.get("input", [])
        input_items: list[InputItem] = []

        # Handle different input formats
        if isinstance(request_input, list):
            for item in request_input:
                if not isinstance(item, dict):
                    raise ValueError("Invalid input item format in Responses API")

                if "type" not in item or item["type"] == "message":
                    role_str = item.get("role", "user")
                    try:
                        role = MessageRole(role_str)
                    except ValueError:
                        role = MessageRole.USER

                    input_items.append(
                        MessageItem(
                            role=role,
                            content=item["content"],
                        ),
                    )
                elif item["type"] == "function_call":
                    input_items.append(
                        FunctionCallItem(
                            call_id=item.get("call_id", ""),
                            name=item.get("name", ""),
                            arguments=item.get("arguments", ""),
                        ),
                    )

        elif isinstance(request_input, str):
            # Simple string input
            input_items.append(
                MessageItem(
                    role=MessageRole.USER,
                    content=request_input,
                ),
            )

        # Extract result from response
        result = None
        finish_reason = None
        output_items: list[OutputItem] = []
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        cached_tokens = None
        reasoning_tokens = None
        system_fingerprint = None

        if not error and response_body:
            # Responses API uses 'output' instead of 'choices'
            output = response_body.get("output")
            if output:
                if isinstance(output, str):
                    # String output - create a simple message item
                    output_items.append(
                        OutputMessageItem(
                            id=f"msg_{response_body.get('id', 'unknown')}",
                            content=[OutputMessageContent(type="text", text=output)],
                            status="completed",
                        ),
                    )
                elif isinstance(output, dict):
                    # Dict output - extract text content
                    text = output.get("content") or output.get("text")
                    if text:
                        output_items.append(
                            OutputMessageItem(
                                id=f"msg_{response_body.get('id', 'unknown')}",
                                content=[OutputMessageContent(type="text", text=text)],
                                status="completed",
                            ),
                        )
                elif isinstance(output, list) and output:
                    # List output - this is the proper Responses API format
                    for idx, item in enumerate(output):
                        if isinstance(item, str):
                            output_items.append(
                                OutputMessageItem(
                                    id=f"msg_{response_body.get('id', 'unknown')}_{idx}",
                                    content=[
                                        OutputMessageContent(type="text", text=item),
                                    ],
                                    status="completed",
                                ),
                            )
                        elif isinstance(item, dict):
                            item_type = item.get("type", "message")
                            if item_type == "message":
                                # Proper message item from Responses API
                                output_items.append(
                                    OutputMessageItem(
                                        id=item.get("id", f"msg_{idx}"),
                                        content=item.get("content", []),
                                        status=item.get("status", "completed"),
                                    ),
                                )
                            else:
                                # Other types - extract text if possible
                                text = item.get("content") or item.get("text")
                                if text:
                                    output_items.append(
                                        OutputMessageItem(
                                            id=f"msg_{response_body.get('id', 'unknown')}_{idx}",
                                            content=[
                                                OutputMessageContent(
                                                    type="text",
                                                    text=str(text),
                                                ),
                                            ],
                                            status="completed",
                                        ),
                                    )

            # Extract finish reason
            finish_reason_str = response_body.get("finish_reason")
            if finish_reason_str:
                try:
                    finish_reason = FinishReason(finish_reason_str)
                except ValueError:
                    pass

            # Extract token usage (same structure as Chat Completions)
            usage = response_body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            completion_tokens = usage.get("completion_tokens") or usage.get(
                "output_tokens",
            )
            total_tokens = usage.get("total_tokens")

            # Additional token metrics
            # Responses API uses input_tokens_details/output_tokens_details
            # Chat Completions API uses prompt_tokens_details/completion_tokens_details
            prompt_tokens_details = (
                usage.get("prompt_tokens_details")
                or usage.get("input_tokens_details")
                or {}
            )
            cached_tokens = prompt_tokens_details.get("cached_tokens")

            completion_tokens_details = (
                usage.get("completion_tokens_details")
                or usage.get("output_tokens_details")
                or {}
            )
            reasoning_tokens = completion_tokens_details.get("reasoning_tokens")

            system_fingerprint = response_body.get("system_fingerprint")

        # Extract tools from request (may be different in Responses API)
        tools = None
        tools_data = request_body.get("tools")
        if tools_data:
            tools = [
                ToolDefinition(
                    type=t.get("type", "function"),
                    function=t.get("function", {}),
                )
                for t in tools_data
            ]

        # Extract other request parameters
        instructions = request_body.get("instructions")
        # Prefer temperature from response (for streaming) if available
        temperature = response_body.get("temperature") or request_body.get(
            "temperature",
        )
        response_format = request_body.get("response_format")

        # Extract project from metadata or use default
        project = (
            metadata.get("project", "Default Project")
            if metadata
            else "Default Project"
        )
        max_tokens = request_body.get("max_tokens")

        return TraceCreate(
            project=project,
            model=model,
            output=output_items,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=call_path,
            tools=tools,
            instructions=instructions,
            prompt=None,
            temperature=temperature,
            tool_choice=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            finish_reason=finish_reason,
            system_fingerprint=system_fingerprint,
            reasoning=None,
            response_schema=response_format,
            trace_metadata=metadata,
            max_tokens=max_tokens,
        )
