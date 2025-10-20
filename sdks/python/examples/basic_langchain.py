"""Basic example of using R4U with LangChain."""

from langchain_core.messages import HumanMessage, SystemMessage
from r4u.tracing.langchain.openai import ChatOpenAI


def main():
    """Run a basic LangChain example with tracing."""

    # Create a LangChain chat model with the callback handler
    llm = ChatOpenAI(
        model="gpt-4o-mini",
    )
    
    # Example 1: Simple message
    print("Example 1: Simple message")
    response = llm.invoke("What is the capital of France?")
    print(f"Response: {response.content}\n")
    
    # Example 2: With system message and chat history
    print("Example 2: With system message and chat history")
    messages = [
        SystemMessage(content="You are a helpful assistant that answers questions concisely."),
        HumanMessage(content="What is Python?"),
    ]
    response = llm.invoke(messages)
    print(f"Response: {response.content}\n")
    
    # Example 3: Using chains with callback config
    print("Example 3: Using with chains")
    from langchain_core.prompts import ChatPromptTemplate
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "{input}")
    ])
    
    chain = prompt | llm
    response = chain.invoke(
        {"input": "Tell me a short joke"},
    )
    print(f"Response: {response.content}\n")


if __name__ == "__main__":
    main()
