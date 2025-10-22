"""LLM executor service for running task implementations using LiteLLM."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from litellm import acompletion

from app.config import Settings
from app.enums import FinishReason, ItemType
from app.models.tasks import Implementation
from app.schemas.traces import InputItem


class ExecutionResult:
    """Result from executing a task implementation."""

    def __init__(
        self,
        started_at: datetime,
        completed_at: datetime,
        prompt_rendered: str,
        result_text: str | None = None,
        result_json: dict[str, Any] | None = None,
        error: str | None = None,
        finish_reason: FinishReason | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cached_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        system_fingerprint: str | None = None,
        provider_response: dict[str, Any] | None = None,
    ):
        self.started_at = started_at
        self.completed_at = completed_at
        self.prompt_rendered = prompt_rendered
        self.result_text = result_text
        self.result_json = result_json
        self.error = error
        self.finish_reason = finish_reason
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.cached_tokens = cached_tokens
        self.reasoning_tokens = reasoning_tokens
        self.system_fingerprint = system_fingerprint
        self.provider_response = provider_response


class LLMExecutor:
    """Executor using LiteLLM for unified LLM provider support."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._setup_litellm()

    def _setup_litellm(self):
        """Setup LiteLLM with API keys from settings."""
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
        if self.settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.settings.google_api_key
        if self.settings.cohere_api_key:
            os.environ["COHERE_API_KEY"] = self.settings.cohere_api_key
        if self.settings.mistral_api_key:
            os.environ["MISTRAL_API_KEY"] = self.settings.mistral_api_key
        if self.settings.together_api_key:
            os.environ["TOGETHER_API_KEY"] = self.settings.together_api_key

    def _render_prompt(
        self, prompt: str, variables: dict[str, Any] | None = None
    ) -> str:
        """Render a prompt template with variables using double curly braces {{ }}."""
        if not variables:
            return prompt

        try:
            # Replace {{variable}} with {variable} for Python's format method
            formatted_prompt = prompt.replace("{{", "{").replace("}}", "}")
            return formatted_prompt.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable in prompt template: {e}")
        except Exception as e:
            raise ValueError(f"Error rendering prompt template: {e}")

    def _render_value(self, value: Any, variables: dict[str, Any] | None) -> Any:
        """Recursively render placeholders in strings within arbitrarily nested structures using double curly braces {{ }}."""
        if variables is None:
            return value
        if isinstance(value, str):
            try:
                # Replace {{variable}} with {variable} for Python's format method
                formatted_value = value.replace("{{", "{").replace("}}", "}")
                return formatted_value.format(**variables)
            except KeyError as e:
                raise ValueError(f"Missing variable in input message template: {e}")
        if isinstance(value, list):
            return [self._render_value(v, variables) for v in value]
        if isinstance(value, dict):
            return {k: self._render_value(v, variables) for k, v in value.items()}
        return value

    def _convert_input_to_messages(
        self, input_items: list[InputItem], variables: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Convert InputItem list to LiteLLM message format, rendering variables in message contents."""
        messages = []

        for item in input_items:
            item_type = getattr(item, "type", None)

            if item_type == ItemType.MESSAGE:
                # Direct message item
                msg = {
                    "role": getattr(item, "role", None),
                    # Render variables inside content which can be str or structured content
                    "content": self._render_value(
                        getattr(item, "content", None), variables
                    ),
                }
                tool_call_id = getattr(item, "tool_call_id", None)
                if tool_call_id:
                    msg["tool_call_id"] = tool_call_id
                tool_calls = getattr(item, "tool_calls", None)
                if tool_calls:
                    # tool_calls are already OpenAI-format dicts per traces schema
                    msg["tool_calls"] = [
                        tc.model_dump() if hasattr(tc, "model_dump") else tc
                        for tc in tool_calls
                    ]
                messages.append(msg)

            elif item_type == ItemType.TOOL_RESULT:
                # Tool result as tool message
                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(getattr(item, "result", None)),
                        "tool_call_id": getattr(item, "call_id", None),
                    }
                )

            elif item_type == ItemType.FUNCTION_RESULT:
                # Function result as function message
                messages.append(
                    {
                        "role": "function",
                        "name": getattr(item, "name", None),
                        "content": json.dumps(getattr(item, "result", None)),
                    }
                )

        return messages

    def _map_finish_reason(self, finish_reason: str | None) -> FinishReason | None:
        """Map LiteLLM finish reason to our enum."""
        if not finish_reason:
            return None

        finish_reason_map = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "tool_calls": FinishReason.TOOL_CALLS,
            "content_filter": FinishReason.CONTENT_FILTER,
            "function_call": FinishReason.FUNCTION_CALL,
        }
        return finish_reason_map.get(finish_reason, FinishReason.STOP)

    async def execute(
        self,
        implementation: Implementation,
        variables: dict[str, Any] | None = None,
        input: list[InputItem] | None = None,
    ) -> ExecutionResult:
        """Execute a task using LiteLLM.

        Args:
            implementation: The implementation to execute
            variables: Variables for prompt template substitution
            input: Optional message history (InputItem list). If provided, messages will follow the system prompt.
        """
        started_at = datetime.now(timezone.utc)

        # Always render prompt as system prompt
        try:
            prompt_rendered = self._render_prompt(implementation.prompt, variables)
        except ValueError as e:
            completed_at = datetime.now(timezone.utc)
            return ExecutionResult(
                started_at=started_at,
                completed_at=completed_at,
                prompt_rendered=implementation.prompt,
                error=str(e),
            )

        # Build messages starting with system prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt_rendered}
        ]
        if input:
            try:
                converted = self._convert_input_to_messages(input, variables)
                messages.extend(converted)
            except Exception as e:
                completed_at = datetime.now(timezone.utc)
                return ExecutionResult(
                    started_at=started_at,
                    completed_at=completed_at,
                    prompt_rendered=prompt_rendered,
                    error=f"Error converting input to messages: {str(e)}",
                )

        # Prepare the request
        model = implementation.model
        temperature = implementation.temperature
        max_tokens = implementation.max_output_tokens
        tools = implementation.tools
        tool_choice = implementation.tool_choice
        response_schema = implementation.response_schema
        reasoning = implementation.reasoning

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if temperature is not None:
            request_params["temperature"] = temperature

        if tools:
            request_params["tools"] = tools

        if tool_choice:
            # Handle both string and dict formats
            if isinstance(tool_choice, dict):
                request_params["tool_choice"] = tool_choice.get("type", "auto")
            else:
                request_params["tool_choice"] = tool_choice

        if response_schema:
            # Map response_schema to OpenAI's response_format
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": response_schema,
            }

        # Handle reasoning for o1/o3 models
        if reasoning:
            if "effort" in reasoning:
                request_params["reasoning_effort"] = reasoning["effort"]

        # Execute the request using LiteLLM
        try:
            response = await acompletion(**request_params)
            completed_at = datetime.now(timezone.utc)

            # Parse the response
            choice = response.choices[0]
            result_text = choice.message.content

            # Try to parse as JSON if response_schema was provided
            result_json = None
            if response_schema and result_text:
                try:
                    result_json = json.loads(result_text)
                except json.JSONDecodeError:
                    pass

            # Map finish reason
            finish_reason = self._map_finish_reason(choice.finish_reason)

            # Extract token usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None
            cached_tokens = (
                getattr(usage, "cached_tokens", None) if usage else None
            )
            reasoning_tokens = (
                getattr(usage, "reasoning_tokens", None) if usage else None
            )

            return ExecutionResult(
                started_at=started_at,
                completed_at=completed_at,
                prompt_rendered=prompt_rendered,
                result_text=result_text,
                result_json=result_json,
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cached_tokens=cached_tokens,
                reasoning_tokens=reasoning_tokens,
                system_fingerprint=getattr(response, "system_fingerprint", None),
                provider_response=(
                    response.model_dump() if hasattr(response, "model_dump") else None
                ),
            )

        except Exception as e:
            completed_at = datetime.now(timezone.utc)
            return ExecutionResult(
                started_at=started_at,
                completed_at=completed_at,
                prompt_rendered=prompt_rendered,
                error=str(e),
            )
