"""Anthropic API parser."""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enums import FinishReason, MessageRole
from app.schemas.traces import (
    FunctionDefinition,
    FunctionToolCallItem,
    InputItem,
    MessageItem,
    OutputItem,
    OutputMessageContent,
    OutputMessageItem,
    ToolCallItem,
    ToolDefinition,
    ToolResultItem,
    TraceCreate,
)
from app.services.parsers.base import ProviderParser


class AnthropicParser(ProviderParser):
    """Parser for Anthropic Claude API format."""

    def can_parse(self, url: str) -> bool:
        """Check if URL is an Anthropic endpoint."""
        parsed = urlparse(url)
        return "anthropic.com" in parsed.netloc or "api.anthropic.com" in parsed.netloc

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
        """Parse Anthropic API request/response."""
        # Extract model
        model = request_body.get("model", "unknown")

        # Extract messages from request (Anthropic format is similar to OpenAI)
        messages = request_body.get("messages", [])
        input_items: list[InputItem] = []

        for msg in messages:
            role_str = msg.get("role", "user")
            content = msg.get("content")

            # Handle content as list (can contain tool_result blocks)
            if isinstance(content, list):
                for block in content:
                    block_type = block.get("type")

                    # Handle tool results
                    if block_type == "tool_result":
                        tool_use_id = block.get("tool_use_id")
                        tool_result_content = block.get("content")
                        # Tool name is not in the result, we'll use a placeholder
                        if tool_use_id:
                            input_items.append(
                                ToolResultItem(
                                    call_id=tool_use_id,
                                    tool_name="unknown",  # Anthropic doesn't include name in result
                                    result=tool_result_content,
                                    is_error=block.get("is_error", False),
                                ),
                            )
                    # Handle regular text content
                    elif block_type == "text":
                        try:
                            role = MessageRole(role_str)
                        except ValueError:
                            role = MessageRole.USER

                        input_items.append(
                            MessageItem(
                                role=role,
                                content=block.get("text"),
                            ),
                        )
            else:
                # Handle content as string
                try:
                    role = MessageRole(role_str)
                except ValueError:
                    role = MessageRole.USER

                input_items.append(
                    MessageItem(
                        role=role,
                        content=content,
                    ),
                )

        # Extract system prompt if present
        system_prompt = request_body.get("system")
        if system_prompt:
            # Add system message at the beginning
            input_items.insert(
                0,
                MessageItem(
                    role=MessageRole.SYSTEM,
                    content=system_prompt,
                ),
            )

        # Extract result from response
        result = None
        finish_reason = None
        output_items: list[OutputItem] = []
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None

        if not error and response_body:
            content = response_body.get("content", [])
            if content:
                # Anthropic returns content as a list of content blocks
                text_blocks = []

                for block in content:
                    block_type = block.get("type")

                    # Handle text blocks
                    if block_type == "text":
                        text = block.get("text", "")
                        text_blocks.append(text)

                    # Handle tool use blocks - create ToolCallItem
                    elif block_type == "tool_use":
                        tool_use_id = block.get("id")
                        tool_name = block.get("name")
                        tool_input = block.get("input", {})

                        if tool_use_id and tool_name:
                            input_items.append(
                                ToolCallItem(
                                    id=tool_use_id,
                                    tool_name=tool_name,
                                    arguments=tool_input,
                                ),
                            )

                            # Also add to output items
                            import json

                            output_items.append(
                                FunctionToolCallItem(
                                    id=tool_use_id,
                                    call_id=tool_use_id,
                                    name=tool_name,
                                    arguments=json.dumps(tool_input),
                                    status="completed",
                                ),
                            )

                # Create output message item if we have text content
                if text_blocks:
                    combined_text = "\n".join(text_blocks)
                    output_items.insert(
                        0,
                        OutputMessageItem(
                            id=f"msg_{response_body.get('id', 'unknown')}",
                            content=[
                                OutputMessageContent(type="text", text=combined_text),
                            ],
                            status="completed",
                        ),
                    )

            # Extract finish reason
            stop_reason = response_body.get("stop_reason")
            if stop_reason:
                # Map Anthropic stop reasons to our enum
                reason_map = {
                    "end_turn": "stop",
                    "max_tokens": "length",
                    "stop_sequence": "stop",
                    "tool_use": "tool_calls",
                }
                finish_reason_str = reason_map.get(stop_reason, stop_reason)
                try:
                    finish_reason = FinishReason(finish_reason_str)
                except ValueError:
                    pass

            # Extract token usage
            usage = response_body.get("usage", {})
            prompt_tokens = usage.get("input_tokens")
            completion_tokens = usage.get("output_tokens")
            if prompt_tokens and completion_tokens:
                total_tokens = prompt_tokens + completion_tokens

        # Extract tools from request
        tools = None
        tools_data = request_body.get("tools")
        if tools_data:
            # Convert Anthropic tool format to OpenAI-like format
            tools = [
                ToolDefinition(
                    type="function",
                    function=FunctionDefinition(
                        name=t.get("name", ""),
                        description=t.get("description"),
                        parameters=t.get("input_schema"),
                    ),
                )
                for t in tools_data
            ]

        # Extract other request parameters
        temperature = request_body.get("temperature")
        max_tokens = request_body.get("max_tokens")

        # Extract project from metadata or use default
        project = (
            metadata.get("project", "Default Project")
            if metadata
            else "Default Project"
        )
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
            instructions=system_prompt,
            prompt=None,
            temperature=temperature,
            tool_choice=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=None,
            reasoning_tokens=None,
            finish_reason=finish_reason,
            system_fingerprint=None,
            reasoning=None,
            response_schema=None,
            trace_metadata=metadata,
            max_tokens=max_tokens,
        )
