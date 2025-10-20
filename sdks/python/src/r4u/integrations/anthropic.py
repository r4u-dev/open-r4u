"""Anthropic integration for R4U observability."""

import inspect
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from unittest.mock import AsyncMock, Mock

from anthropic import Anthropic as OriginalAnthropic
from anthropic import AsyncAnthropic as OriginalAsyncAnthropic

from r4u.integrations.http.tracer import AbstractTracer, RequestInfo

from .http.httpx import trace_async_client, trace_client

from ..client import R4UClient, r4u_client
from ..utils import extract_call_path


class AnthropicWrapper:
    """Wrapper for Anthropic client that automatically creates traces."""

    def __init__(self, client: Any, r4u_client: R4UClient, project: str):
        """Initialize the wrapper.

        Args:
            client: Original Anthropic client
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        self._original_client = client
        self._r4u_client = r4u_client
        self._project = project

        # Wrap the messages
        if hasattr(client, "messages"):
            self.messages = MessagesWrapper(client.messages, r4u_client, project)
        else:
            self.messages = client.messages if hasattr(client, "messages") else None

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_client, name)


class MessagesWrapper:
    """Wrapper for Anthropic messages that creates traces."""

    def __init__(self, messages_client: Any, r4u_client: R4UClient, project: str):
        """Initialize the wrapper.

        Args:
            messages_client: Original messages client
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        self._original_messages = messages_client
        self._r4u_client = r4u_client
        self._project = project
        self._is_async = inspect.iscoroutinefunction(messages_client.create)

    def create(self, **kwargs) -> Any:
        """Create message with tracing.

        This method handles both sync and async Anthropic clients.
        For AsyncAnthropic, this returns a coroutine that should be awaited.
        """
        if self._is_async:
            return self._trace_message_async(self._original_messages.create, **kwargs)
        return self._trace_message(self._original_messages.create, **kwargs)

    async def acreate(self, **kwargs) -> Any:
        """Create message asynchronously with tracing."""
        return await self._trace_message_async(self._original_messages.create, **kwargs)

    def _trace_message(self, original_method: Any, **kwargs) -> Any:
        """Trace a synchronous message call."""
        started_at = datetime.utcnow()
        call_path, _ = extract_call_path()

        try:
            result = original_method(**kwargs)
            completed_at = datetime.utcnow()

            response_content = self._extract_response_content(result)
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_content=response_content,
                error=None,
                project=self._project,
                result=result,
            )
            self._create_trace_sync(**payload)

            return result
        except Exception as exc:  # pragma: no cover - re-raised immediately
            completed_at = datetime.utcnow()
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_content=None,
                error=exc,
                project=self._project,
                result=None,
            )
            self._create_trace_sync(**payload)
            raise

    async def _trace_message_async(self, original_method: Any, **kwargs) -> Any:
        """Trace an asynchronous message call."""
        started_at = datetime.utcnow()
        call_path, _ = extract_call_path()

        try:
            result = await original_method(**kwargs)
            completed_at = datetime.utcnow()

            response_content = self._extract_response_content(result)
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_content=response_content,
                error=None,
                project=self._project,
                result=result,
            )
            await self._create_trace_async(**payload)

            return result
        except Exception as exc:  # pragma: no cover - re-raised immediately
            completed_at = datetime.utcnow()
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_content=None,
                error=exc,
                project=self._project,
                result=None,
            )
            await self._create_trace_async(**payload)
            raise

    def _create_trace_sync(self, **kwargs):
        """Create trace synchronously."""
        try:
            kwargs["project"] = self._project
            self._r4u_client.create_trace(**kwargs)
        except Exception as error:  # pragma: no cover - defensive logging
            print(f"Failed to create trace: {error}")

    async def _create_trace_async(self, **kwargs):
        """Create trace asynchronously."""
        try:
            kwargs["project"] = self._project
            await self._r4u_client.create_trace_async(**kwargs)
        except Exception as error:  # pragma: no cover - defensive logging
            print(f"Failed to create trace: {error}")

    @staticmethod
    def _to_plain(value: Any) -> Any:
        """Convert Anthropic SDK models into plain Python structures."""
        if isinstance(value, (Mock, AsyncMock)):
            allowed_keys = {
                "id",
                "type",
                "name",
                "description",
                "parameters",
                "metadata",
                "role",
                "content",
                "tool_use",
                "tool_result",
                "stop_reason",
                "stop_sequence",
                "usage",
            }
            extracted = {
                key: MessagesWrapper._to_plain(val)
                for key, val in vars(value).items()
                if key in allowed_keys
            }
            if extracted:
                return extracted
            return value
        if isinstance(value, dict):
            return {key: MessagesWrapper._to_plain(val) for key, val in value.items()}
        if isinstance(value, list):
            return [MessagesWrapper._to_plain(item) for item in value]
        if isinstance(value, tuple):
            return tuple(MessagesWrapper._to_plain(item) for item in value)
        if isinstance(value, BaseModel):
            return MessagesWrapper._to_plain(value.model_dump())
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            if isinstance(dumped, (dict, list, tuple)):
                return MessagesWrapper._to_plain(dumped)
            return dumped
        if hasattr(value, "dict"):
            dumped = value.dict()
            if isinstance(dumped, (dict, list, tuple)):
                return MessagesWrapper._to_plain(dumped)
            return dumped
        if hasattr(value, "__dict__"):
            public_attrs = {
                key: MessagesWrapper._to_plain(val)
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
            if public_attrs:
                return public_attrs
        return value

    @classmethod
    def _normalize_tool_use(cls, tool_use: Any) -> Dict[str, Any]:
        """Normalize a tool use definition from the Anthropic response."""
        plain = cls._to_plain(tool_use)
        if not isinstance(plain, dict):
            return {}

        tool_type = plain.get("type")
        if tool_type is not None and not isinstance(tool_type, str):
            plain["type"] = str(tool_type)

        return plain

    @classmethod
    def _normalize_message(cls, message: Any) -> Dict[str, Any]:
        """Normalize request or response messages for trace payloads."""
        plain = cls._to_plain(message)
        if not isinstance(plain, dict):
            return {"content": plain}

        normalized: Dict[str, Any] = dict(plain)
        role = normalized.get("role")
        if role is not None and not isinstance(role, str):
            normalized["role"] = str(role)

        if "content" in normalized:
            normalized["content"] = cls._to_plain(normalized["content"])

        tool_use = normalized.get("tool_use")
        if tool_use:
            normalized["tool_use"] = cls._normalize_tool_use(tool_use)

        tool_result = normalized.get("tool_result")
        if tool_result:
            normalized["tool_result"] = cls._to_plain(tool_result)

        return normalized

    @classmethod
    def _prepare_trace_messages(cls, messages_input: Any) -> List[Dict[str, Any]]:
        """Convert the request messages into trace-friendly dictionaries."""
        if not messages_input:
            return []
        return [cls._normalize_message(message) for message in messages_input]

    @classmethod
    def _extract_response_content(cls, result: Any) -> Optional[str]:
        """Extract the assistant content from the message result."""
        content = getattr(result, "content", None)
        if content is None:
            return None
        
        # Handle list of content blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    text_parts.append(block.text)
            return "".join(text_parts) if text_parts else None
        
        # Handle single text content
        if isinstance(content, str):
            return content
        
        # Handle content objects
        if hasattr(content, "text"):
            return content.text
        
        return None

    @classmethod
    def _extract_tool_definitions(cls, kwargs: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Extract tool definitions from the request payload."""
        definitions: List[Dict[str, Any]] = []

        for tool in kwargs.get("tools") or []:
            plain = cls._to_plain(tool)
            if not isinstance(plain, dict):
                continue
            
            definition = {
                "name": plain.get("name"),
                "description": plain.get("description"),
                "input_schema": plain.get("input_schema"),
            }
            definition = {k: v for k, v in definition.items() if v is not None}
            if definition.get("name"):
                definitions.append(definition)

        return definitions or None

    @classmethod
    def _extract_token_usage(cls, result: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Extract token usage from the message result."""
        usage = getattr(result, "usage", None)
        if usage is None:
            return None, None, None
        
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        
        # Calculate total if not provided
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        
        return input_tokens, output_tokens, total_tokens

    @classmethod
    def _build_trace_payload(
        cls,
        *,
        kwargs: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        call_path: str,
        response_content: Optional[str],
        error: Optional[Exception],
        project: str,
        result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Assemble the payload sent to the trace API."""
        # Only include input messages, not the response
        trace_messages = cls._prepare_trace_messages(kwargs.get("messages") or [])

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", "unknown"),
            "messages": trace_messages,
            "started_at": started_at,
            "completed_at": completed_at,
            "path": call_path,
            "project": project,
        }

        tools = cls._extract_tool_definitions(kwargs)
        if tools:
            payload["tools"] = tools

        if response_content is not None:
            payload["result"] = response_content
        if error is not None:
            payload["error"] = str(error)

        # Extract token usage if result is available
        if result is not None and error is None:
            input_tokens, output_tokens, total_tokens = cls._extract_token_usage(result)
            if input_tokens is not None:
                payload["prompt_tokens"] = input_tokens
            if output_tokens is not None:
                payload["completion_tokens"] = output_tokens
            if total_tokens is not None:
                payload["total_tokens"] = total_tokens

        # Extract response_format/schema if provided
        response_format = kwargs.get("response_format")
        if response_format is not None:
            # Handle different response_format types
            if hasattr(response_format, "model_dump"):
                # Pydantic model
                payload["response_schema"] = response_format.model_dump()
            elif isinstance(response_format, dict):
                # Plain dict
                payload["response_schema"] = response_format

        return payload

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_messages, name)


def wrap_anthropic(
    client: Any,
    api_url: str = "http://localhost:8000",
    timeout: float = 30.0,
    project: Optional[str] = None,
) -> AnthropicWrapper:
    """Wrap an Anthropic client to automatically create traces.
    
    Args:
        client: Anthropic client to wrap
        api_url: R4U API URL
        timeout: HTTP timeout
        project: Project name for traces. If not provided, uses R4U_PROJECT env variable or defaults to "Default Project"
    """
    if project is None:
        project = os.getenv("R4U_PROJECT", "Default Project")
    r4u_client = R4UClient(api_url=api_url, timeout=timeout)
    return AnthropicWrapper(client, r4u_client, project)


def get_messages_trace(request_info: RequestInfo) -> Optional[Dict[str, Any]]:
    """Trace a messages request."""
    request_json = json.loads(request_info.request_payload)
    print(f"{request_info.method.upper()} {request_info.url}")
    print(json.dumps(request_json, indent=2))


class AnthropicTracer(AbstractTracer):
    """Tracer for Anthropic client."""
    def __init__(self, r4u_client: R4UClient):
        self._r4u_client = r4u_client

    def trace_request(self, request_info: RequestInfo):
        """Trace a request."""
        if request_info.url.endswith("/messages"):
            trace = get_messages_trace(request_info)
        else:
            raise ValueError(f"Unsupported request: {request_info.url}")

        if trace is not None:
            self._r4u_client.create_trace(**trace)


class Anthropic(OriginalAnthropic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_client(self._client, AnthropicTracer(r4u_client))


class AsyncAnthropic(OriginalAsyncAnthropic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_async_client(self._client, AnthropicTracer(r4u_client))
