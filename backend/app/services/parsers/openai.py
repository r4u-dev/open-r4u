"""OpenAI API parser."""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enums import FinishReason, MessageRole
from app.schemas.traces import (
    InputItem,
    MessageItem,
    Reasoning,
    ToolCallItem,
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

    def parse(
        self,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        call_path: str | None = None,
    ) -> TraceCreate:
        """Parse OpenAI API request/response.

        Supports both Chat Completions API and the new Responses API.
        """
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
                if tool_call_id and name:
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

            # Regular message without tool calls
            input_items.append(
                MessageItem(
                    role=role,
                    content=msg.get("content"),
                ),
            )

        # Extract result from response
        result = None
        finish_reason = None
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
                result = message.get("content")

                # Handle tool calls from assistant response
                tool_calls_data = message.get("tool_calls")
                if tool_calls_data:
                    for tc in tool_calls_data:
                        function_data = tc.get("function", {})
                        arguments_str = function_data.get("arguments", "")

                        # Parse arguments if they're a JSON string
                        import json

                        try:
                            arguments = (
                                json.loads(arguments_str)
                                if isinstance(arguments_str, str)
                                else arguments_str
                            )
                        except (json.JSONDecodeError, TypeError):
                            arguments = {"raw": arguments_str}

                        input_items.append(
                            ToolCallItem(
                                id=tc.get("id", ""),
                                tool_name=function_data.get("name", ""),
                                arguments=arguments,
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
            usage = response_body.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

            # Additional token metrics
            if "prompt_tokens_details" in usage:
                cached_tokens = usage["prompt_tokens_details"].get("cached_tokens")

            if "completion_tokens_details" in usage:
                reasoning_tokens = usage["completion_tokens_details"].get(
                    "reasoning_tokens",
                )

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
        task_id = metadata.get("task_id") if metadata else None
        max_tokens = request_body.get("max_tokens")

        return TraceCreate(
            project=project,
            model=model,
            result=result,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=call_path,
            task_id=task_id,
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
                if isinstance(item, dict):
                    # If it looks like a message
                    if "role" in item:
                        role_str = item.get("role", "user")
                        try:
                            role = MessageRole(role_str)
                        except ValueError:
                            role = MessageRole.USER

                        input_items.append(
                            MessageItem(
                                role=role,
                                content=item.get("content"),
                            ),
                        )
                    else:
                        # Generic content
                        input_items.append(
                            MessageItem(
                                role=MessageRole.USER,
                                content=str(item),
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
                    result = output
                elif isinstance(output, dict):
                    result = output.get("content") or output.get("text")
                elif isinstance(output, list) and output:
                    # If output is a list, join text content
                    texts = []
                    for item in output:
                        if isinstance(item, str):
                            texts.append(item)
                        elif isinstance(item, dict):
                            texts.append(item.get("content") or item.get("text") or "")
                    result = "\n".join(texts) if texts else None

            # Extract finish reason
            finish_reason_str = response_body.get("finish_reason")
            if finish_reason_str:
                try:
                    finish_reason = FinishReason(finish_reason_str)
                except ValueError:
                    pass

            # Extract token usage (same structure as Chat Completions)
            usage = response_body.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            completion_tokens = usage.get("completion_tokens") or usage.get(
                "output_tokens",
            )
            total_tokens = usage.get("total_tokens")

            # Additional token metrics
            if "prompt_tokens_details" in usage:
                cached_tokens = usage["prompt_tokens_details"].get("cached_tokens")

            if "completion_tokens_details" in usage:
                reasoning_tokens = usage["completion_tokens_details"].get(
                    "reasoning_tokens",
                )

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
        temperature = request_body.get("temperature")
        response_format = request_body.get("response_format")

        # Extract project from metadata or use default
        project = (
            metadata.get("project", "Default Project")
            if metadata
            else "Default Project"
        )
        task_id = metadata.get("task_id") if metadata else None
        max_tokens = request_body.get("max_tokens")

        return TraceCreate(
            project=project,
            model=model,
            result=result,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=call_path,
            task_id=task_id,
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
