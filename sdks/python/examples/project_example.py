"""Example showing how to create traces with R4U SDK."""

# Example 1: Creating a basic trace
print("Example 1: Creating a basic trace")
from r4u.client import get_r4u_client
client = get_r4u_client()
trace = client.create_trace(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello World"}],
    result="Hello! How can I help you?",
)
print(f"Created trace {trace.id} in project_id {trace.project_id}")

# Example 2: Creating another trace
print("\nExample 2: Creating another trace")
trace2 = client.create_trace(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "What's the weather?"}],
    result="I don't have access to real-time weather data.",
)
print(f"Created trace {trace2.id} in project_id {trace2.project_id}")

# Example 3: Using tracing wrappers
print("\nExample 3: Using tracing wrappers")
from r4u.tracing.openai import wrap_openai

# The wrap_openai function creates traces automatically
print("When using wrap_openai() or wrap_langchain(),")
print("they will automatically create traces for your LLM calls.")

print("\nAll examples completed successfully!")
