"""OpenAI API parser."""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.schemas.traces import (
    TraceCreate,
)
from app.services.parsers.base import ProviderParser


class OpenAIParser(ProviderParser):
    """Parser for OpenAI API format."""

    def can_parse(self, url: str) -> bool:
        """Check if URL is an OpenAI endpoint."""
        parsed = urlparse(url)
        return "openai.com" in parsed.netloc or "api.openai.com" in parsed.netloc

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
        request_path: str | None = None,
    ) -> TraceCreate:
        """Parse OpenAI API request/response.

        Supports both Chat Completions API and the new Responses API.
        Also handles streaming responses.
        """
        model = request_body.get("model") or response_body.get("model") or "unknown"

        # Determine API type
        is_responses_api = False
        if (request_path and "/responses" in request_path) or (
            response_body and response_body.get("object") == "response"
        ):
            is_responses_api = True

        input_items = self._parse_input(request_body)
        output_items = []
        usage = None
        finish_reason = None
        system_fingerprint = None

        if is_streaming and streaming_response:
            if is_responses_api:
                output_items, usage, finish_reason, system_fingerprint = (
                    self._parse_responses_streaming(streaming_response)
                )
            else:
                output_items, usage, finish_reason, system_fingerprint = (
                    self._parse_completions_streaming(streaming_response)
                )
        elif is_responses_api:
            output_items, usage, finish_reason, system_fingerprint = (
                self._parse_responses_non_streaming(response_body)
            )
        else:
            output_items, usage, finish_reason, system_fingerprint = (
                self._parse_completions_non_streaming(response_body)
            )

        trace = TraceCreate(
            model=model,
            path=call_path,
            started_at=started_at,
            completed_at=completed_at,
            error=error,
            input=input_items,
            output=output_items,
            finish_reason=finish_reason,
            system_fingerprint=system_fingerprint,
            trace_metadata=metadata,
            instructions=request_body.get("instructions"),
            prompt=request_body.get("prompt"),
        )

        if usage:
            trace.prompt_tokens = usage.get("prompt_tokens") or usage.get(
                "input_tokens",
            )
            trace.completion_tokens = usage.get("completion_tokens") or usage.get(
                "output_tokens",
            )
            trace.total_tokens = usage.get("total_tokens")

        return trace

    def _parse_input(self, request_body: dict[str, Any]) -> list[Any]:
        messages = request_body.get("messages", [])
        if not messages and "input" in request_body:
            input_val = request_body["input"]
            if isinstance(input_val, list):
                messages = input_val
            elif isinstance(input_val, str):
                messages = [{"role": "user", "content": input_val}]

        input_items = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            tool_calls = msg.get("tool_calls")

            if tool_calls:
                # Assistant message with tool calls
                for tc in tool_calls:
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            import json

                            args = json.loads(args)
                        except:
                            args = {}

                    input_items.append(
                        {
                            "type": "tool_call",
                            "id": tc.get("id"),
                            "tool_name": func.get("name"),
                            "arguments": args,
                        },
                    )

            elif role == "tool":
                # Tool result
                input_items.append(
                    {
                        "type": "tool_result",
                        "call_id": msg.get("tool_call_id"),
                        "tool_name": None,
                        "result": content,
                        "is_error": False,  # Can't determine easily
                    },
                )
            else:
                input_items.append(
                    {"type": "message", "role": role, "content": content},
                )
        return input_items

    def _parse_completions_non_streaming(self, response_body: dict[str, Any]):
        choices = response_body.get("choices", [])
        output_items = []
        finish_reason = None

        for choice in choices:
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")

            tool_calls = message.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    output_items.append(
                        {
                            "type": "function_call",  # Trace schema has FunctionToolCallItem with type="function_call"
                            "id": tc.get("id"),
                            "call_id": tc.get("id"),  # Redundant?
                            "name": func.get("name"),
                            "arguments": func.get(
                                "arguments",
                            ),  # Schema expects string for FunctionToolCallItem
                            "status": "completed",
                        },
                    )
            else:
                output_items.append(
                    {
                        "type": "message",
                        "id": response_body.get("id", ""),
                        "role": message.get("role", "assistant"),
                        "content": [{"type": "text", "text": message.get("content")}],
                        "status": "completed",
                    },
                )

        usage = response_body.get("usage")
        system_fingerprint = response_body.get("system_fingerprint")
        return output_items, usage, finish_reason, system_fingerprint

    def _parse_completions_streaming(self, streaming_response: str):
        lines = streaming_response.strip().split("\n")
        full_content = ""
        role = "assistant"
        finish_reason = None
        system_fingerprint = None
        response_id = ""
        tool_calls_buffer = {}  # index -> {id, type, function: {name, arguments}}

        for line in lines:
            line = line.strip()
            if not line.startswith("data: "):
                continue

            data_str = line[6:]
            if data_str == "[DONE]":
                break

            try:
                import json

                chunk = json.loads(data_str)
                response_id = chunk.get("id", response_id)
                system_fingerprint = (
                    chunk.get("system_fingerprint") or system_fingerprint
                )

                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})

                    # Handle content
                    content = delta.get("content")
                    if content:
                        full_content += content

                    if delta.get("role"):
                        role = delta.get("role")

                    # Handle tool calls
                    if delta.get("tool_calls"):
                        for tc in delta.get("tool_calls"):
                            idx = tc.get("index")
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {
                                    "id": "",
                                    "function": {"name": "", "arguments": ""},
                                }

                            if tc.get("id"):
                                tool_calls_buffer[idx]["id"] = tc.get("id")

                            func = tc.get("function", {})
                            if func.get("name"):
                                tool_calls_buffer[idx]["function"]["name"] += func.get(
                                    "name",
                                )
                            if func.get("arguments"):
                                tool_calls_buffer[idx]["function"]["arguments"] += (
                                    func.get("arguments")
                                )

                    if choices[0].get("finish_reason"):
                        finish_reason = choices[0].get("finish_reason")
            except Exception:
                pass

        output_items = []
        if full_content:
            output_items.append(
                {
                    "type": "message",
                    "id": response_id,
                    "role": role,
                    "content": [{"type": "text", "text": full_content}],
                    "status": "completed",
                },
            )

        for idx in sorted(tool_calls_buffer.keys()):
            tc = tool_calls_buffer[idx]
            output_items.append(
                {
                    "type": "function_call",
                    "id": tc["id"],
                    "call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                    "status": "completed",
                },
            )

        usage = None
        return output_items, usage, finish_reason, system_fingerprint

    def _parse_responses_non_streaming(self, response_body: dict[str, Any]):
        output_data = response_body.get("output", [])
        output_items = []

        for item in output_data:
            if item.get("type") == "message":
                content_list = item.get("content", [])
                converted_content = []
                for c in content_list:
                    if c.get("type") == "output_text":
                        converted_content.append(
                            {"type": "text", "text": c.get("text")},
                        )

                output_items.append(
                    {
                        "type": "message",
                        "id": item.get("id"),
                        "role": item.get("role"),
                        "content": converted_content,
                        "status": item.get("status"),
                    },
                )
            elif (
                item.get("type") == "function_call"
            ):  # Assuming Responses API uses this type for tools
                output_items.append(
                    {
                        "type": "function_call",
                        "id": item.get("id"),
                        "call_id": item.get("call_id") or item.get("id"),
                        "name": item.get("name"),
                        "arguments": item.get("arguments"),
                        "status": item.get("status"),
                    },
                )

        usage = response_body.get("usage")
        finish_reason = "stop" if response_body.get("status") == "completed" else None
        system_fingerprint = None

        return output_items, usage, finish_reason, system_fingerprint

    def _parse_responses_streaming(self, streaming_response: str):
        lines = streaming_response.strip().split("\n")
        messages = {}
        tool_calls = {}  # id -> {name, arguments, status}
        usage = None
        finish_reason = None

        for line in lines:
            line = line.strip()
            if not line.startswith("data: "):
                continue

            data_str = line[6:]
            try:
                import json

                event_data = json.loads(data_str)
                event_type = event_data.get("type")

                if event_type == "response.output_item.added":
                    item = event_data.get("item", {})
                    if item.get("type") == "message":
                        messages[item["id"]] = {
                            "role": item.get("role"),
                            "content": "",
                            "status": item.get("status"),
                        }
                    elif item.get("type") == "function_call":
                        tool_calls[item["id"]] = {
                            "name": item.get("name"),
                            "arguments": item.get("arguments"),
                            "status": item.get("status"),
                            "call_id": item.get("call_id"),
                        }

                elif event_type == "response.output_text.delta":
                    item_id = event_data.get("item_id")
                    delta = event_data.get("delta", "")
                    if item_id in messages:
                        messages[item_id]["content"] += delta

                # Assuming similar delta events for tool calls if they exist in Responses API streaming

                elif event_type == "response.output_item.done":
                    item = event_data.get("item", {})
                    if item.get("type") == "message":
                        if item["id"] in messages:
                            messages[item["id"]]["status"] = item.get("status")
                    elif item.get("type") == "function_call":
                        if item["id"] in tool_calls:
                            tool_calls[item["id"]]["status"] = item.get("status")

                elif event_type == "response.completed":
                    response = event_data.get("response", {})
                    usage = response.get("usage")
                    if response.get("status") == "completed":
                        finish_reason = "stop"

            except Exception:
                pass

        output_items = []
        for msg_id, msg_data in messages.items():
            output_items.append(
                {
                    "type": "message",
                    "id": msg_id,
                    "role": msg_data["role"],
                    "content": [{"type": "text", "text": msg_data["content"]}],
                    "status": msg_data["status"],
                },
            )

        for tc_id, tc_data in tool_calls.items():
            output_items.append(
                {
                    "type": "function_call",
                    "id": tc_id,
                    "call_id": tc_data.get("call_id") or tc_id,
                    "name": tc_data["name"],
                    "arguments": tc_data["arguments"],
                    "status": tc_data["status"],
                },
            )

        return output_items, usage, finish_reason, None
