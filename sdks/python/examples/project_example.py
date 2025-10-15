"""Example showing how to use projects with R4U SDK."""

import os
from r4u.client import R4UClient

# Example 1: Using default project
print("Example 1: Creating trace with default project")
client = R4UClient(api_url="http://localhost:8000")
trace = client.create_trace(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello World"}],
    result="Hello! How can I help you?",
)
print(f"Created trace {trace.id} in project_id {trace.project_id}")

# Example 2: Using custom project
print("\nExample 2: Creating trace with custom project")
trace2 = client.create_trace(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "What's the weather?"}],
    result="I don't have access to real-time weather data.",
    project="Weather Bot",
)
print(f"Created trace {trace2.id} in project_id {trace2.project_id}")

# Example 3: Using environment variable
print("\nExample 3: Using R4U_PROJECT environment variable")
os.environ["R4U_PROJECT"] = "Environment Project"

# This would be used in integrations
from r4u.integrations.openai import wrap_openai

# The wrap_openai function will use R4U_PROJECT env variable if project param is not specified
print(f"Environment variable R4U_PROJECT is set to: {os.environ['R4U_PROJECT']}")
print("When using wrap_openai() or wrap_langchain() without project param,")
print("they will automatically use the R4U_PROJECT environment variable.")

print("\nAll examples completed successfully!")
