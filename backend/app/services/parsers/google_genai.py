"""Google Generative AI API parser."""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enums import FinishReason, MessageRole
from app.schemas.traces import (
    FunctionCallItem,
    FunctionResultItem,
    FunctionToolCallItem,
    InputItem,
    MessageItem,
    OutputItem,
    OutputMessageContent,
    OutputMessageItem,
    TraceCreate,
)
from app.services.parsers.base import ProviderParser


class GoogleGenAIParser(ProviderParser):
    """Parser for Google Generative AI API format."""

    def can_parse(self, url: str) -> bool:
        """Check if URL is a Google GenAI endpoint."""
        parsed = urlparse(url)
        return (
            "googleapis.com" in parsed.netloc
            or "generativelanguage.googleapis.com" in parsed.netloc
        )

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
        """Parse Google GenAI API request/response."""
        # Extract model from URL or metadata (Google uses model in URL path)
        model = metadata.get("model", "unknown") if metadata else "unknown"

        # Extract contents from request (Google format)
        contents = request_body.get("contents", [])
        input_items: list[InputItem] = []

        for content in contents:
            role_str = content.get("role", "user")
            # Map Google roles to our MessageRole
            role_map = {
                "user": MessageRole.USER,
                "model": MessageRole.ASSISTANT,
            }
            role = role_map.get(role_str, MessageRole.USER)

            # Extract parts (Google uses parts instead of content)
            parts = content.get("parts", [])

            for part in parts:
                # Handle text parts
                if "text" in part:
                    input_items.append(
                        MessageItem(
                            role=role,
                            content=part.get("text"),
                        ),
                    )

                # Handle function calls
                elif "functionCall" in part:
                    func_call = part["functionCall"]
                    func_name = func_call.get("name", "")
                    func_args = func_call.get("args", {})

                    # Generate a unique ID for the function call
                    func_id = f"fc_{func_name}_{len(input_items)}"

                    input_items.append(
                        FunctionCallItem(
                            call_id=func_id,
                            name=func_name,
                            arguments=func_args,
                        ),
                    )

                # Handle function responses
                elif "functionResponse" in part:
                    func_response = part["functionResponse"]
                    func_name = func_response.get("name", "")
                    response_data = func_response.get("response", {})

                    # Generate a unique ID for the function call
                    func_id = f"fc_{func_name}_{len(input_items)}"

                    input_items.append(
                        FunctionResultItem(
                            call_id=func_id,
                            name=func_name,
                            result=response_data,
                        ),
                    )

        # Extract system instruction if present
        system_instruction = request_body.get("systemInstruction")
        if system_instruction and isinstance(system_instruction, dict):
            parts = system_instruction.get("parts", [])
            text_parts = [part.get("text", "") for part in parts if "text" in part]
            if text_parts:
                input_items.insert(
                    0,
                    MessageItem(
                        role=MessageRole.SYSTEM,
                        content="\n".join(text_parts),
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
            candidates = response_body.get("candidates", [])
            if candidates:
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                text_parts = []

                for part in parts:
                    # Handle text parts
                    if "text" in part:
                        text_parts.append(part.get("text", ""))

                    # Handle function calls in response
                    elif "functionCall" in part:
                        func_call = part["functionCall"]
                        func_name = func_call.get("name", "")
                        func_args = func_call.get("args", {})

                        # Generate a unique ID for the function call
                        func_id = f"fc_{func_name}_{len(input_items)}"

                        input_items.append(
                            FunctionCallItem(
                                call_id=func_id,
                                name=func_name,
                                arguments=func_args,
                            ),
                        )

                        # Also add to output items
                        import json

                        output_items.append(
                            FunctionToolCallItem(
                                id=func_id,
                                call_id=func_id,
                                name=func_name,
                                arguments=json.dumps(func_args),
                                status="completed",
                            ),
                        )

                # Create output message item if we have text content
                if text_parts:
                    combined_text = "\n".join(text_parts)
                    output_items.insert(
                        0,
                        OutputMessageItem(
                            id=f"msg_{response_body.get('name', 'unknown')}",
                            content=[
                                OutputMessageContent(type="text", text=combined_text),
                            ],
                            status="completed",
                        ),
                    )

                # Extract finish reason
                finish_reason_str = candidate.get("finishReason")
                if finish_reason_str:
                    # Map Google finish reasons to our enum
                    reason_map = {
                        "STOP": "stop",
                        "MAX_TOKENS": "length",
                        "SAFETY": "content_filter",
                        "RECITATION": "content_filter",
                    }
                    mapped_reason = reason_map.get(finish_reason_str, "stop")
                    try:
                        finish_reason = FinishReason(mapped_reason)
                    except ValueError:
                        pass

            # Extract token usage
            usage_metadata = response_body.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount")
            completion_tokens = usage_metadata.get("candidatesTokenCount")
            total_tokens = usage_metadata.get("totalTokenCount")

        # Extract generation config
        generation_config = request_body.get("generationConfig", {})
        temperature = generation_config.get("temperature")

        # Extract project from metadata or use default
        project = (
            metadata.get("project", "Default Project")
            if metadata
            else "Default Project"
        )
        task_id = metadata.get("task_id") if metadata else None
        max_tokens = generation_config.get("maxOutputTokens")

        return TraceCreate(
            project=project,
            model=model,
            output=output_items,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            input=input_items,
            path=call_path,
            task_id=task_id,
            tools=None,  # TODO: Parse Google tools if needed
            instructions=None,
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
