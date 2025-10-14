"""Demonstrate automatic tracing of tool calls with the OpenAI wrapper.

This example uses an in-memory fake OpenAI client so it can run without external
dependencies. When the wrapped client is invoked, the R4U OpenAI integration
automatically records a trace that includes:

* Tool definitions supplied in the request
* An assistant message that issues a tool call
* A tool role response in the conversation history
* The final assistant answer that incorporates the tool output

Make sure the R4U backend is running locally on http://localhost:8000 before
executing this script so the trace can be persisted.
"""

from typing import Any, Dict, List

from r4u.integrations.openai import wrap_openai


class _FakeChoice:
    """Minimal stand-in for an OpenAI ChatCompletion choice."""

    def __init__(self, message: Dict[str, Any]):
        self.message = message


class _FakeResponse:
    """Container that mimics the structure of an OpenAI response."""

    def __init__(self, choices: List[_FakeChoice]):
        self.choices = choices


class _FakeCompletions:
    """Fake completions client that emits a tool-informed assistant reply."""

    def create(self, **kwargs: Any) -> _FakeResponse:
        tool_call_id = kwargs["messages"][2]["tool_calls"][0]["id"]

        assistant_message = {
            "role": "assistant",
            "content": "It's currently 22°C and clear in Paris, with humidity around 48%.",
            "metadata": {
                "sourced_from_tool_call": tool_call_id,
            },
        }
        return _FakeResponse([_FakeChoice(assistant_message)])


class _FakeChat:
    """Namespace mirroring openai.chat."""

    def __init__(self):
        self.completions = _FakeCompletions()


class FakeOpenAIClient:
    """Lightweight OpenAI-like client used just for this example."""

    def __init__(self):
        self.chat = _FakeChat()


def main() -> None:
    """Call the wrapped fake OpenAI client with tool usage metadata."""
    openai_client = FakeOpenAIClient()
    traced_client = wrap_openai(openai_client, api_url="http://localhost:8000")

    tool_call_id = "call_lookup_weather_1"

    request_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {
            "role": "user",
            "content": "What's the weather like in Paris right now?",
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": "lookup_weather",
                        "arguments": {"location": "Paris, FR"},
                    },
                }
            ],
        },
        {
            "role": "tool",
            "name": "lookup_weather",
            "tool_call_id": tool_call_id,
            "content": {
                "temperature_c": 22,
                "conditions": "clear",
                "humidity": 0.48,
            },
        },
    ]

    tool_definitions = [
        {
            "type": "function",
            "function": {
                "name": "lookup_weather",
                "description": "Retrieve the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country to look up.",
                        }
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    chat_completions = traced_client.chat
    assert chat_completions is not None  # Guard for type-checkers

    response = chat_completions.completions.create(
        model="gpt-4.1-mini",
        messages=request_messages,
        tools=tool_definitions,
    )

    print(response.choices[0].message["content"])
    print("Trace with tool usage sent to R4U API. Check your dashboard for details.")


if __name__ == "__main__":
    main()
