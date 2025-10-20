"""Anthropic API parser."""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enums import FinishReason, MessageRole
from app.schemas.traces import (
    FunctionDefinition,
    InputItem,
    MessageItem,
    ToolDefinition,
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
    ) -> TraceCreate:
        """Parse Anthropic API request/response."""
        
        # Extract model
        model = request_body.get("model", "unknown")
        
        # Extract messages from request (Anthropic format is similar to OpenAI)
        messages = request_body.get("messages", [])
        input_items: list[InputItem] = []
        
        for msg in messages:
            role_str = msg.get("role", "user")
            try:
                role = MessageRole(role_str)
            except ValueError:
                role = MessageRole.USER
            
            input_items.append(
                MessageItem(
                    role=role,
                    content=msg.get("content"),
                    name=msg.get("name"),
                )
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
                )
            )
        
        # Extract result from response
        result = None
        finish_reason = None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        
        if not error and response_body:
            content = response_body.get("content", [])
            if content:
                # Anthropic returns content as a list of content blocks
                text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
                result = "\n".join(text_blocks) if text_blocks else None
            
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
        project = metadata.get("project", "Default Project") if metadata else "Default Project"
        path = metadata.get("path") if metadata else None
        task_id = metadata.get("task_id") if metadata else None
        
        return TraceCreate(
            project=project,
            model=model,
            result=result,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=path,
            task_id=task_id,
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
        )
