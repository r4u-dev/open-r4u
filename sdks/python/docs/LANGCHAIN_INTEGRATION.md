# LangChain Integration for R4U

This integration provides automatic tracing for LangChain applications, capturing all LLM calls, message history, and tool usage.

## Installation

```bash
pip install langchain-core langchain-openai  # or other LangChain packages
```

## Quick Start

### Basic Usage

```python
from langchain_openai import ChatOpenAI
from r4u.tracing.langchain import wrap_langchain

# Create the R4U callback handler
r4u_handler = wrap_langchain(api_url="http://localhost:8000")

# Add handler to your LangChain model
llm = ChatOpenAI(model="gpt-3.5-turbo", callbacks=[r4u_handler])

# All LLM calls will be automatically traced
response = llm.invoke("What is the capital of France?")
```

### With Chains

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "{input}")
])

chain = prompt | llm
response = chain.invoke(
    {"input": "Tell me a joke"},
    config={"callbacks": [r4u_handler]}
)
```

## Features

### 1. Automatic Message Tracking

The integration automatically captures all messages in a conversation:

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Message history is automatically captured
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="My name is Alice."),
    AIMessage(content="Nice to meet you, Alice!"),
    HumanMessage(content="What's my name?"),
]

llm = ChatOpenAI(callbacks=[r4u_handler])
response = llm.invoke(messages)

# All 5 messages (including the response) will be in the trace
```

### 2. Tool/Function Call Tracking

Tool calls are automatically tracked:

```python
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    return f"Weather in {location}: Sunny"

tools = [get_weather]
llm_with_tools = ChatOpenAI(callbacks=[r4u_handler]).bind_tools(tools)

# Tool calls will be captured in the trace
response = llm_with_tools.invoke("What's the weather in Paris?")
```

### 3. Agent Tracing

Works seamlessly with LangChain agents:

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

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

# All intermediate LLM calls will be traced
result = agent_executor.invoke({
    "input": "What's the weather in Tokyo and calculate 25 * 4"
})
```

### 4. Memory/Conversation History

The integration captures full conversation context:

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

memory = ConversationBufferMemory()
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    callbacks=[r4u_handler]
)

# First message
conversation.predict(input="Hi, I'm Bob")

# Second message - memory is included in trace
conversation.predict(input="What's my name?")

# The trace will include all messages from memory
```

## Advanced Usage

### Custom Configuration

```python
# Configure with custom API URL and timeout
r4u_handler = wrap_langchain(
    api_url="https://your-r4u-instance.com",
    timeout=60.0
)
```

### Multiple Handlers

You can use multiple callback handlers:

```python
from langchain.callbacks import StdOutCallbackHandler

r4u_handler = wrap_langchain()
stdout_handler = StdOutCallbackHandler()

llm = ChatOpenAI(callbacks=[r4u_handler, stdout_handler])
```

### Async Support

The integration works with async LangChain operations:

```python
llm = ChatOpenAI(callbacks=[r4u_handler])

# Async invocation is automatically traced
response = await llm.ainvoke("Hello")
```

## What Gets Traced?

Each trace includes:

- **Model name**: The LLM model being used
- **Messages**: All input messages and the response
- **Tools**: Tool/function definitions if provided
- **Tool calls**: Any tool calls made by the model
- **Result**: The final text response (if any)
- **Timestamps**: Start and completion times
- **Call path**: Where in your code the LLM was called
- **Errors**: Any errors that occurred

## Trace Structure

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Hello"}
  ],
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather",
      "parameters": {...}
    }
  ],
  "result": "Hi there!",
  "started_at": "2024-01-15T10:00:00",
  "completed_at": "2024-01-15T10:00:02",
  "path": "main.py::chat_function"
}
```

**Note**: The messages array contains only the input messages sent to the LLM. The assistant's response is stored in the `result` field to avoid duplication. This makes it easy to see the exact input that was sent and get quick access to the output.

## Supported LangChain Components

- ✅ Chat Models (ChatOpenAI, ChatAnthropic, etc.)
- ✅ LLMs (OpenAI, Anthropic, etc.)
- ✅ Chains (LLMChain, SequentialChain, etc.)
- ✅ Agents (OpenAI Functions, ReAct, etc.)
- ✅ Tools/Functions
- ✅ Memory/Conversation History
- ✅ Async operations

## Examples

See the `examples/` directory for complete working examples:

- `basic_langchain.py` - Simple LangChain usage
- `advanced_langchain.py` - Memory, tools, and agents

## Troubleshooting

### Handler not capturing traces

Make sure the handler is passed to the LangChain component:

```python
# ✅ Correct
llm = ChatOpenAI(callbacks=[r4u_handler])

# ❌ Won't work
llm = ChatOpenAI()
llm.invoke("Hello")  # No handler attached
```

### Missing message history

Ensure you're passing all messages:

```python
# ✅ Correct - passes all history
messages = [system_msg, user_msg_1, ai_msg_1, user_msg_2]
response = llm.invoke(messages)

# ⚠️ Only current message traced
response = llm.invoke("Hello")
```

### Tool calls not showing

Make sure tools are bound to the model:

```python
# ✅ Correct
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke("What's the weather?")

# ❌ Won't capture tools
response = llm.invoke("What's the weather?")
```

## API Reference

### `wrap_langchain(api_url, timeout)`

Create a LangChain callback handler for R4U tracing.

**Parameters:**
- `api_url` (str): R4U API base URL (default: "http://localhost:8000")
- `timeout` (float): HTTP request timeout in seconds (default: 30.0)

**Returns:**
- `R4UCallbackHandler`: Callback handler to use with LangChain

**Raises:**
- `ImportError`: If langchain-core is not installed

### `R4UCallbackHandler`

LangChain callback handler that creates traces in R4U.

This class implements the LangChain callback interface and should not be instantiated directly. Use `wrap_langchain()` instead.

## Comparison with OpenAI Integration

| Feature | OpenAI Integration | LangChain Integration |
|---------|-------------------|----------------------|
| Usage | `client = wrap_openai(OpenAI())` | `handler = wrap_langchain()` |
| Scope | OpenAI calls only | All LLM providers |
| Memory | Manual | Automatic |
| Agents | Not supported | Fully supported |
| Tools | Supported | Fully supported |
| Chains | Not applicable | Fully supported |

## License

Same as the parent project.
