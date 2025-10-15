"""Example demonstrating structured output tracking with LangChain integration."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from r4u.integrations.langchain import wrap_langchain

# Define a Pydantic model for structured output
class Person(BaseModel):
    """Information about a person."""
    name: str = Field(description="The person's full name")
    age: int = Field(description="The person's age in years")
    occupation: str = Field(description="The person's occupation")
    city: str = Field(description="The city where the person lives")


# Create the R4U callback handler
r4u_handler = wrap_langchain(
    api_url="http://localhost:8000",
    project="LangChain Structured Output Demo"
)

# Create a LangChain model
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[r4u_handler])

# Use with_structured_output for automatic schema enforcement
print("Example: Structured output with automatic schema tracking")
print("=" * 60)

structured_llm = llm.with_structured_output(Person)
response = structured_llm.invoke(
    "Generate information about a fictional software engineer living in San Francisco"
)

print(f"Response type: {type(response)}")
print(f"Name: {response.name}")
print(f"Age: {response.age}")
print(f"Occupation: {response.occupation}")
print(f"City: {response.city}")
print()
print("✓ Response schema automatically tracked in trace!")
print("✓ Token usage automatically tracked in trace!")
print()
print("=" * 60)
print("Check the R4U dashboard to see the trace with:")
print("  - response_schema: The Pydantic model schema")
print("  - prompt_tokens, completion_tokens, total_tokens")
print("  - Full message history and result")
