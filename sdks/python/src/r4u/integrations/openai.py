"""OpenAI integration for R4U observability."""

import inspect
import json
import os
from datetime import datetime
import types
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from unittest.mock import AsyncMock, Mock

from openai import OpenAI as OriginalOpenAI
from openai import AsyncOpenAI as OriginalAsyncOpenAI

from .http.httpx import trace_async_client, trace_client

from ..client import R4UClient
from ..utils import extract_call_path


class OpenAIWrapper:
    """Wrapper for OpenAI client that automatically creates traces."""

    def __init__(self, client: Any, r4u_client: R4UClient, project: str):
        """Initialize the wrapper.

        Args:
            client: Original OpenAI client
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        self._original_client = client
        self._r4u_client = r4u_client
        self._project = project

        # Wrap the chat completions
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            self.chat = ChatCompletionsWrapper(client.chat, r4u_client, project)
        else:
            self.chat = client.chat if hasattr(client, "chat") else None

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_client, name)


class ChatCompletionsWrapper:
    """Wrapper for OpenAI chat completions."""

    def __init__(self, chat_client: Any, r4u_client: R4UClient, project: str):
        """Initialize the wrapper.

        Args:
            chat_client: Original chat client
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        self._original_chat = chat_client
        self._r4u_client = r4u_client
        self._project = project
        self.completions = CompletionsWrapper(chat_client.completions, r4u_client, project)

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_chat, name)


class CompletionsWrapper:
    """Wrapper for OpenAI completions that creates traces."""

    def __init__(self, completions_client: Any, r4u_client: R4UClient, project: str):
        """Initialize the wrapper.

        Args:
            completions_client: Original completions client
            r4u_client: R4U client for creating traces
            project: Project name for traces
        """
        self._original_completions = completions_client
        self._r4u_client = r4u_client
        self._project = project
        self._is_async = inspect.iscoroutinefunction(completions_client.create)

    def create(self, **kwargs) -> Any:
        """Create completion with tracing.

        This method handles both sync and async OpenAI clients.
        For AsyncOpenAI, this returns a coroutine that should be awaited.
        """
        if self._is_async:
            return self._trace_completion_async(self._original_completions.create, **kwargs)
        return self._trace_completion(self._original_completions.create, **kwargs)

    async def acreate(self, **kwargs) -> Any:
        """Create completion asynchronously with tracing."""
        return await self._trace_completion_async(self._original_completions.create, **kwargs)

    def _trace_completion(self, original_method: Any, **kwargs) -> Any:
        """Trace a synchronous completion call."""
        started_at = datetime.utcnow()
        call_path, _ = extract_call_path()

        try:
            result = original_method(**kwargs)
            completed_at = datetime.utcnow()

            response_message = self._extract_response_message(result)
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_message=response_message,
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
                response_message=None,
                error=exc,
                project=self._project,
                result=None,
            )
            self._create_trace_sync(**payload)
            raise

    async def _trace_completion_async(self, original_method: Any, **kwargs) -> Any:
        """Trace an asynchronous completion call."""
        started_at = datetime.utcnow()
        call_path, _ = extract_call_path()

        try:
            result = await original_method(**kwargs)
            completed_at = datetime.utcnow()

            response_message = self._extract_response_message(result)
            payload = self._build_trace_payload(
                kwargs=kwargs,
                started_at=started_at,
                completed_at=completed_at,
                call_path=call_path,
                response_message=response_message,
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
                response_message=None,
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
        """Convert OpenAI SDK models into plain Python structures."""
        if isinstance(value, (Mock, AsyncMock)):
            allowed_keys = {
                "id",
                "type",
                "function",
                "arguments",
                "name",
                "description",
                "parameters",
                "metadata",
                "role",
                "content",
                "tool_calls",
                "delta",
                "message",
            }
            extracted = {
                key: CompletionsWrapper._to_plain(val)
                for key, val in vars(value).items()
                if key in allowed_keys
            }
            if extracted:
                return extracted
            return value
        if isinstance(value, dict):
            return {key: CompletionsWrapper._to_plain(val) for key, val in value.items()}
        if isinstance(value, list):
            return [CompletionsWrapper._to_plain(item) for item in value]
        if isinstance(value, tuple):
            return tuple(CompletionsWrapper._to_plain(item) for item in value)
        if isinstance(value, BaseModel):
            return CompletionsWrapper._to_plain(value.model_dump())
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            if isinstance(dumped, (dict, list, tuple)):
                return CompletionsWrapper._to_plain(dumped)
            return dumped
        if hasattr(value, "dict"):
            dumped = value.dict()
            if isinstance(dumped, (dict, list, tuple)):
                return CompletionsWrapper._to_plain(dumped)
            return dumped
        if hasattr(value, "__dict__"):
            public_attrs = {
                key: CompletionsWrapper._to_plain(val)
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
            if public_attrs:
                return public_attrs
        return value

    @classmethod
    def _normalize_tool_call(cls, tool_call: Any) -> Dict[str, Any]:
        """Normalize a tool call definition from the OpenAI response."""
        plain = cls._to_plain(tool_call)
        if not isinstance(plain, dict):
            return {}

        tool_type = plain.get("type")
        if tool_type is not None and not isinstance(tool_type, str):
            plain["type"] = str(tool_type)

        function = plain.get("function")
        if isinstance(function, dict):
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    function["arguments"] = json.loads(arguments)
                except (ValueError, TypeError):
                    pass

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

        tool_calls = normalized.get("tool_calls")
        if tool_calls:
            normalized["tool_calls"] = [
                call
                for call in (cls._normalize_tool_call(tool_call) for tool_call in tool_calls)
                if call
            ]
            if not normalized["tool_calls"]:
                normalized.pop("tool_calls", None)

        function_call = normalized.pop("function_call", None)
        if function_call:
            tool_call = cls._normalize_tool_call({"type": "function", "function": function_call})
            normalized.setdefault("tool_calls", []).append(tool_call)

        return normalized

    @classmethod
    def _prepare_trace_messages(cls, messages_input: Any) -> List[Dict[str, Any]]:
        """Convert the request messages into trace-friendly dictionaries."""
        if not messages_input:
            return []
        return [cls._normalize_message(message) for message in messages_input]

    @classmethod
    def _extract_response_message(cls, result: Any) -> Optional[Dict[str, Any]]:
        """Extract the assistant message from the completion result."""
        choices = getattr(result, "choices", None)
        if not choices:
            return None
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is None:
            message = getattr(first_choice, "delta", None)
        if message is None and isinstance(first_choice, dict):
            message = first_choice.get("message") or first_choice.get("delta")
        if message is None:
            choice_plain = cls._to_plain(first_choice)
            if isinstance(choice_plain, dict):
                message = choice_plain.get("message") or choice_plain.get("delta")
        return message

    @classmethod
    def _extract_tool_definitions(cls, kwargs: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Extract tool definitions from the request payload."""
        definitions: List[Dict[str, Any]] = []

        for tool in kwargs.get("tools") or []:
            plain = cls._to_plain(tool)
            if not isinstance(plain, dict):
                continue
            function = plain.get("function") or {}
            if not isinstance(function, dict):
                function = cls._to_plain(function) or {}
            metadata = {k: v for k, v in plain.items() if k not in {"type", "function"}}
            definition = {
                "name": function.get("name"),
                "description": function.get("description"),
                "parameters": function.get("parameters"),
                "type": plain.get("type") or "function",
            }
            if metadata:
                definition["metadata"] = metadata
            definition = {k: v for k, v in definition.items() if v is not None}
            if definition.get("name"):
                definitions.append(definition)

        for function in kwargs.get("functions") or []:
            plain = cls._to_plain(function)
            if not isinstance(plain, dict):
                continue
            metadata = {k: v for k, v in plain.items() if k not in {"name", "description", "parameters", "type"}}
            definition = {
                "name": plain.get("name"),
                "description": plain.get("description"),
                "parameters": plain.get("parameters"),
                "type": plain.get("type") or "function",
            }
            if metadata:
                definition["metadata"] = metadata
            definition = {k: v for k, v in definition.items() if v is not None}
            if definition.get("name"):
                definitions.append(definition)

        return definitions or None

    @classmethod
    def _extract_token_usage(cls, result: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Extract token usage from the completion result."""
        usage = getattr(result, "usage", None)
        if usage is None:
            return None, None, None
        
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        
        return prompt_tokens, completion_tokens, total_tokens

    @classmethod
    def _build_trace_payload(
        cls,
        *,
        kwargs: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        call_path: str,
        response_message: Optional[Any],
        error: Optional[Exception],
        project: str,
        result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Assemble the payload sent to the trace API."""
        # Only include input messages, not the response
        trace_messages = cls._prepare_trace_messages(kwargs.get("messages") or [])
        result_text: Optional[str] = None

        # Extract result text from response, but don't add to messages array
        if response_message is not None:
            assistant_message = cls._normalize_message(response_message)
            assistant_message.setdefault("role", "assistant")
            content = assistant_message.get("content")
            # Only set result if there's actual text content
            if isinstance(content, str) and content.strip():
                result_text = content

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

        if result_text is not None:
            payload["result"] = result_text
        if error is not None:
            payload["error"] = str(error)

        # Extract token usage if result is available
        if result is not None and error is None:
            prompt_tokens, completion_tokens, total_tokens = cls._extract_token_usage(result)
            if prompt_tokens is not None:
                payload["prompt_tokens"] = prompt_tokens
            if completion_tokens is not None:
                payload["completion_tokens"] = completion_tokens
            if total_tokens is not None:
                payload["total_tokens"] = total_tokens

        # Extract response_format/schema if provided
        response_format = kwargs.get("response_format")
        if response_format is not None:
            # Handle different response_format types
            if hasattr(response_format, "json_schema"):
                # Structured output with json_schema
                schema = getattr(response_format.json_schema, "schema", None)
                if schema:
                    payload["response_schema"] = cls._to_plain(schema)
            elif hasattr(response_format, "model_dump"):
                # Pydantic model
                payload["response_schema"] = response_format.model_dump()
            elif isinstance(response_format, dict):
                # Plain dict
                if "json_schema" in response_format:
                    schema = response_format["json_schema"].get("schema")
                    if schema:
                        payload["response_schema"] = schema
                elif "type" not in response_format or response_format.get("type") != "json_object":
                    # Only include if it's not just {"type": "json_object"}
                    payload["response_schema"] = response_format

        return payload

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original client."""
        return getattr(self._original_completions, name)


def wrap_openai(
    client: Any,
    api_url: str = "http://localhost:8000",
    timeout: float = 30.0,
    project: Optional[str] = None,
) -> OpenAIWrapper:
    """Wrap an OpenAI client to automatically create traces.
    
    Args:
        client: OpenAI client to wrap
        api_url: R4U API URL
        timeout: HTTP timeout
        project: Project name for traces. If not provided, uses R4U_PROJECT env variable or defaults to "Default Project"
    """
    if project is None:
        project = os.getenv("R4U_PROJECT", "Default Project")
    r4u_client = R4UClient(api_url=api_url, timeout=timeout)
    return OpenAIWrapper(client, r4u_client, project)


class OpenAI(OriginalOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_client(self._client, OpenAITracer(R4UClient()))


class AsyncOpenAI(OriginalAsyncOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trace_async_client(self._client)
