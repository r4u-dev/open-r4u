"""LLM executor service for running task implementations using LiteLLM."""

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

from litellm import acompletion

from app.config import Settings
from app.enums import FinishReason, ItemType
from app.models.tasks import Implementation
from app.schemas.executions import ExecutionResultBase
from app.schemas.traces import (
    FunctionToolCallItem,
    InputItem,
    OutputItem,
    OutputMessageContent,
    OutputMessageItem,
    ToolCallItem,
)

logger = logging.getLogger(__name__)


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

    def _render_template(
        self,
        value: Any,
        variables: dict[str, Any] | None = None,
    ) -> Any:
        """Render template variables using double curly braces {{ }}.
        
        Recursively processes strings, lists, and dicts. Only {{ }} placeholders 
        are substituted; single braces are left untouched.
        
        Args:
            value: String, list, dict, or other value to render
            variables: Variable substitutions (key -> value)
            raise_on_missing: If True, raise ValueError on missing vars; 
                            if False, log warning and return original
        
        Returns:
            Rendered value with {{ var }} replaced by variables[var]

        """
        if variables is None:
            return value

        if isinstance(value, str):
            # Early exit if no template markers
            if "{{" not in value:
                return value

            def replace_match(match: re.Match[str]) -> str:
                key = match.group(1).strip()
                if key not in variables:
                    logger.warning(f"Missing variable in template: {key}")
                    return match.group(0)
                return str(variables[key])

            try:
                return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace_match, value)
            except ValueError:
                logger.warning(f"Missing variable in template: {value}")
                return value
            except Exception as e:
                logger.warning(f"Error rendering template: {e}")
                return value

        elif isinstance(value, list):
            return [self._render_template(v, variables) for v in value]
        elif isinstance(value, dict):
            return {k: self._render_template(v, variables) for k, v in value.items()}
        else:
            return value

    def _convert_input_to_messages(
        self,
        input_items: list[InputItem],
        variables: dict[str, Any] | None,
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
                    "content": self._render_template(
                        getattr(item, "content", None),
                        variables,
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
                    },
                )

            elif item_type == ItemType.FUNCTION_RESULT:
                # Function result as function message
                messages.append(
                    {
                        "role": "function",
                        "name": getattr(item, "name", None),
                        "content": json.dumps(getattr(item, "result", None)),
                    },
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

    def _build_response_format(self, response_schema: dict[str, Any] | None) -> dict[str, Any] | None:
        """Normalize response schema into OpenAI response_format json_schema structure.

        Accepts either the new wrapped format or a plain JSON Schema and returns
        the proper response_format payload. Returns None if no schema provided.
        """
        if not response_schema:
            return None

        # If already in the new format, pass through
        if (
            isinstance(response_schema, dict)
            and response_schema.get("type") == "json_schema"
            and isinstance(response_schema.get("json_schema"), dict)
            and "schema" in response_schema["json_schema"]
        ):
            return response_schema

        # Otherwise, wrap the plain JSON schema
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response_schema",
                "strict": True,
                "schema": response_schema,
            },
        }

    async def execute(
        self,
        implementation: Implementation,
        variables: dict[str, Any] | None = None,
        input: list[InputItem] | None = None,
    ) -> ExecutionResultBase:
        """Execute a task using LiteLLM.

        Args:
            implementation: The implementation to execute
            variables: Variables for prompt template substitution
            input: Optional message history (InputItem list). If provided, messages will follow the system prompt.

        """
        started_at = datetime.now(UTC)

        # Always render prompt as system prompt (warn on missing, do not fail)
        prompt_rendered = self._render_template(implementation.prompt, variables)

        # Build messages starting with system prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt_rendered},
        ]
        if input:
            try:
                converted = self._convert_input_to_messages(input, variables)
                messages.extend(converted)
            except Exception as e:
                completed_at = datetime.now(UTC)
                return ExecutionResultBase(
                    started_at=started_at,
                    completed_at=completed_at,
                    prompt_rendered=prompt_rendered,
                    error=f"Error converting input to messages: {e!s}",
                )

        # Prepare the request
        model = implementation.model
        if not model or "/" not in model:
            logger.warning("Executing implementation %s with non-canonical model '%s'", implementation.id, model)

        temperature = implementation.temperature
        max_tokens = implementation.max_output_tokens
        tools = implementation.tools
        tool_choice = implementation.tool_choice
        response_schema = implementation.task.response_schema
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
            request_params["response_format"] = self._build_response_format(response_schema)

        # Handle reasoning for o1/o3 models
        if reasoning:
            if "effort" in reasoning:
                request_params["reasoning_effort"] = reasoning["effort"]

        # Execute the request using LiteLLM
        try:
            response = await acompletion(**request_params, drop_params=True)
            completed_at = datetime.now(UTC)

            # Parse the response
            choice = response.choices[0]
            result_text = choice.message.content

            # Build output items list (OutputItem schema format)
            output_items: list[OutputItem] = []
            response_id = getattr(response, "id", "unknown")

            # Add tool calls as FunctionToolCallItem to output_items,
            # and create a human-readable result_text if only tools are present and no main message.
            tool_calls = []
            if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    arguments_str = (
                        json.dumps(tc.function.arguments)
                        if isinstance(tc.function.arguments, dict)
                        else (
                            tc.function.arguments
                            if isinstance(tc.function.arguments, str)
                            else json.dumps(tc.function.arguments)
                        )
                    )
                    output_items.append(
                        FunctionToolCallItem(
                            id=tc.id,
                            call_id=tc.id,
                            name=tc.function.name,
                            arguments=arguments_str,
                            status="completed",
                        ),
                    )
                    tool_calls.append(
                        f"{tc.function.name}({arguments_str})"
                    )

            # Add assistant message to output as OutputMessageItem if present.
            if result_text:
                output_items.append(
                    OutputMessageItem(
                        id=f"msg_{response_id}",
                        content=[OutputMessageContent(type="text", text=result_text)],
                        status="completed",
                    ),
                )
            elif tool_calls:
                # If there is no assistant message, make result_text a human readable string listing tool calls.
                result_text = "Tool calls: " + ", ".join(tool_calls)

            # Set result_json to the list of OutputItems (proper schema format)
            result_json = [item.model_dump() for item in output_items] if output_items else None

            # Map finish reason
            finish_reason = self._map_finish_reason(choice.finish_reason)

            # Extract token usage
            usage = response.usage

            # Default values
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None

            # Cached_tokens extraction (handle dicts and objects; avoid hasattr with MagicMock)
            cached_tokens = None
            if usage:
                prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
                if prompt_tokens_details is not None:
                    if isinstance(prompt_tokens_details, dict):
                        cached_tokens = prompt_tokens_details.get("cached_tokens")
                    else:
                        value = getattr(prompt_tokens_details, "cached_tokens", None)
                        if value is not None:
                            cached_tokens = value
                if cached_tokens is None:
                    direct = getattr(usage, "cached_tokens", None)
                    if direct is not None:
                        cached_tokens = direct

            # Reasoning_tokens extraction (handle dicts and objects)
            reasoning_tokens = None
            if usage:
                completion_tokens_details = getattr(
                    usage, "completion_tokens_details", None,
                )
                if completion_tokens_details is not None:
                    if isinstance(completion_tokens_details, dict):
                        reasoning_tokens = completion_tokens_details.get(
                            "reasoning_tokens",
                        )
                    else:
                        value = getattr(
                            completion_tokens_details, "reasoning_tokens", None,
                        )
                        if value is not None:
                            reasoning_tokens = value
                if reasoning_tokens is None:
                    direct = getattr(usage, "reasoning_tokens", None)
                    if direct is not None:
                        reasoning_tokens = direct

            return ExecutionResultBase(
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
            logger.error(f"Error executing implementation: {e!s}")
            completed_at = datetime.now(UTC)
            return ExecutionResultBase(
                started_at=started_at,
                completed_at=completed_at,
                prompt_rendered=prompt_rendered,
                error=str(e),
            )
