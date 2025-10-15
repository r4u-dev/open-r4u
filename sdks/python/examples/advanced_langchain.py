"""Advanced LangChain example with memory and tool calls."""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from r4u.integrations.langchain import wrap_langchain


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.
    
    Args:
        location: The city name
    """
    # This is a mock implementation
    return f"The weather in {location} is sunny and 72°F"


@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression.
    
    Args:
        expression: The mathematical expression to evaluate
    """
    try:
        result = eval(expression)  # In production, use a safe math parser
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    """Run advanced LangChain examples with tracing."""
    # Create the R4U callback handler
    r4u_handler = wrap_langchain(api_url="http://localhost:8000")
    
    # Example 1: Chat with memory (message history)
    print("=" * 60)
    print("Example 1: Chat with message history")
    print("=" * 60)
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        callbacks=[r4u_handler]
    )
    
    # Simulate a conversation with memory
    conversation_history = [
        SystemMessage(content="You are a helpful assistant with memory of our conversation."),
        HumanMessage(content="My name is Alice and I live in Paris."),
    ]
    
    # First turn
    response = llm.invoke(conversation_history)
    print(f"User: My name is Alice and I live in Paris.")
    print(f"Assistant: {response.content}\n")
    
    # Add response to history
    conversation_history.append(response)
    
    # Second turn - reference previous context
    conversation_history.append(HumanMessage(content="What's my name and where do I live?"))
    response = llm.invoke(conversation_history)
    print(f"User: What's my name and where do I live?")
    print(f"Assistant: {response.content}\n")
    
    # Example 2: Tool/function calling
    print("=" * 60)
    print("Example 2: Tool/Function calling")
    print("=" * 60)
    
    # Create model with tools
    tools = [get_weather, calculate]
    llm_with_tools = ChatOpenAI(
        model="gpt-3.5-turbo",
        callbacks=[r4u_handler]
    ).bind_tools(tools)
    
    # Ask a question that requires tool use
    response = llm_with_tools.invoke("What's the weather in San Francisco?")
    print(f"User: What's the weather in San Francisco?")
    
    # Check if model wants to use tools
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"Assistant wants to call tool: {response.tool_calls[0]['name']}")
        print(f"With arguments: {response.tool_calls[0]['args']}\n")
    else:
        print(f"Assistant: {response.content}\n")
    
    # Example 3: Agent with tools (requires langchain-agents)
    try:
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate
        
        print("=" * 60)
        print("Example 3: Agent with multiple tool calls")
        print("=" * 60)
        
        # Create agent prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant with access to tools."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Create agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            callbacks=[r4u_handler],
            verbose=True
        )
        
        # Run agent
        result = agent_executor.invoke({
            "input": "What's the weather in Tokyo and also calculate 25 * 4"
        })
        print(f"\nFinal result: {result['output']}\n")
        
    except ImportError:
        print("Skipping agent example (requires langchain package)")


if __name__ == "__main__":
    main()
