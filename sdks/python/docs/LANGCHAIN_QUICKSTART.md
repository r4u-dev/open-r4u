# Quick Start: LangChain Integration

## Installation

```bash
# Install the SDK with LangChain support
uv add langchain-core langchain-openai

# Or with pip
pip install langchain-core langchain-openai
```

## Basic Usage

```python
from langchain_openai import ChatOpenAI
from r4u.tracing.langchain import wrap_langchain

# 1. Create the R4U callback handler
r4u_handler = wrap_langchain(api_url="http://localhost:8000")

# 2. Add it to your LangChain model
llm = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[r4u_handler])

# 3. Use LangChain normally - all calls are automatically traced
response = llm.invoke("What is the capital of France?")
print(response.content)
```

That's it! Every LLM call will now be traced in your R4U platform.

## With Message History (Memory)

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Create handler
r4u_handler = wrap_langchain()
llm = ChatOpenAI(callbacks=[r4u_handler])

# All messages in the conversation are automatically captured
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="My name is Alice and I live in Paris."),
]

response = llm.invoke(messages)
messages.append(response)

# Continue the conversation - full history is in the trace
messages.append(HumanMessage(content="What's my name and where do I live?"))
response = llm.invoke(messages)

# The trace will contain ALL messages from the conversation
```

## With Tools/Function Calling

```python
from langchain_core.tools import tool

# Define tools
@tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    return f"The weather in {location} is sunny and 72°F"

# Add tools to the model
tools = [get_weather]
r4u_handler = wrap_langchain()
llm = ChatOpenAI(callbacks=[r4u_handler]).bind_tools(tools)

# Tool calls are automatically tracked
response = llm.invoke("What's the weather in Paris?")

# The trace will include:
# - Tool definitions
# - Tool calls made by the model
```

## With Chains

```python
from langchain_core.prompts import ChatPromptTemplate

r4u_handler = wrap_langchain()
llm = ChatOpenAI(callbacks=[r4u_handler])

# Create a chain
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "{input}")
])

chain = prompt | llm

# Chain invocations are automatically traced
response = chain.invoke({"input": "Tell me a joke"})
```

## With Agents

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# Create agent with tools
r4u_handler = wrap_langchain()
llm = ChatOpenAI(callbacks=[r4u_handler])

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[r4u_handler]
)

# All agent steps are traced
result = agent_executor.invoke({
    "input": "What's the weather in Tokyo and Paris?"
})
```

## Async Support

```python
# Works with async operations too
r4u_handler = wrap_langchain()
llm = ChatOpenAI(callbacks=[r4u_handler])

response = await llm.ainvoke("Hello!")
```

## What Gets Traced?

Each trace includes:

- **Model name**: The LLM model being used
- **Messages**: All input messages (user, system, assistant from history)
- **Tools**: Tool/function definitions if provided
- **Result**: The final text response from the LLM (not duplicated in messages)
- **Timestamps**: Start and completion times
- **Call path**: Where in your code the LLM was called
- **Errors**: Any errors that occurred

Note: The assistant's response is stored in the `result` field for quick access, not added to the messages array to avoid duplication.

## Configuration

```python
# Custom API URL and timeout
r4u_handler = wrap_langchain(
    api_url="https://your-r4u-instance.com",
    timeout=60.0
)
```

## See Also

- **Full Documentation**: [docs/LANGCHAIN_INTEGRATION.md](LANGCHAIN_INTEGRATION.md)
- **Basic Examples**: [examples/basic_langchain.py](../examples/basic_langchain.py)
- **Advanced Examples**: [examples/advanced_langchain.py](../examples/advanced_langchain.py)
