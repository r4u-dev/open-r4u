"""Example demonstrating automatic token tracking with LangChain integration."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from r4u.integrations.langchain import wrap_langchain

# Create the R4U callback handler
r4u_handler = wrap_langchain(
    api_url="http://localhost:8000",
    project="LangChain Token Tracking Demo"
)

# Create a LangChain model with the R4U callback handler
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    callbacks=[r4u_handler]
)

# Example 1: Simple chat completion with automatic token tracking
print("Example 1: Simple chat with automatic token tracking")
print("=" * 60)
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is the capital of France?")
]
response = llm.invoke(messages)
print(f"Response: {response.content}")
print("✓ Token usage automatically tracked in trace!")
print()

# Example 2: Longer conversation
print("Example 2: Longer conversation")
print("=" * 60)
messages = [
    SystemMessage(content="You are a knowledgeable geography teacher."),
    HumanMessage(content="Tell me about the capital cities of Europe. Just name 3 of them briefly.")
]
response = llm.invoke(messages)
print(f"Response: {response.content}")
print("✓ Token usage automatically tracked in trace!")
print()

# Example 3: Using with chains
print("Example 3: Using with chains")
print("=" * 60)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that answers questions concisely."),
    ("user", "{input}")
])

chain = prompt | llm | StrOutputParser()

# The callbacks are passed through the chain automatically
result = chain.invoke(
    {"input": "What is 2+2?"},
    config={"callbacks": [r4u_handler]}
)
print(f"Response: {result}")
print("✓ Token usage automatically tracked in trace!")
print()

print("=" * 60)
print("Check the R4U dashboard to see all traces with token usage!")
print("Each trace will show:")
print("  - prompt_tokens: Number of tokens in the input")
print("  - completion_tokens: Number of tokens in the response")
print("  - total_tokens: Total tokens used")
