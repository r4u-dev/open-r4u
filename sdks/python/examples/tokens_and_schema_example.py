"""Example demonstrating token usage and response schema tracking with R4U."""

from openai import OpenAI
from r4u.tracing.openai import wrap_openai

# Initialize OpenAI client
client = OpenAI()

# Wrap it with R4U observability
wrapped_client = wrap_openai(
    client,
    api_url="http://localhost:8000"
)

# Example 1: Basic completion with automatic token tracking
print("Example 1: Basic completion with automatic token tracking")
response = wrapped_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)
print(f"Response: {response.choices[0].message.content}")
print(f"Tokens used - Prompt: {response.usage.prompt_tokens}, "
      f"Completion: {response.usage.completion_tokens}, "
      f"Total: {response.usage.total_tokens}")
print()

# Example 2: Structured output with response_schema tracking
print("Example 2: Structured output with response_schema")
response = wrapped_client.chat.completions.create(
    model="gpt-4o-mini",  # json_schema is supported in gpt-4o, gpt-4o-mini, gpt-4-turbo
    messages=[
        {"role": "user", "content": "Generate information about a fictional person"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person_info",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "occupation": {"type": "string"},
                    "city": {"type": "string"}
                },
                "required": ["name", "age", "occupation", "city"],  # All properties required when strict=True
                "additionalProperties": False
            },
            "strict": True
        }
    }
)
print(f"Response: {response.choices[0].message.content}")
print(f"Tokens: {response.usage.total_tokens}")
print("Note: The response_schema is automatically tracked in the trace!")
print()