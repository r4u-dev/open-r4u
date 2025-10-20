"""Example usage of R4U LangChain Google GenAI integration."""

import os

from langchain_openai import ChatOpenAI

from r4u.tracing import trace_all
from r4u.client import ConsoleTracer

trace_all(ConsoleTracer())

def main():
    """Example of using LangChain OpenAI with R4U tracing."""
    
    # Initialize the model with tracing
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # Generate content - this will be automatically traced
    response = llm.invoke("What is the capital of France?")
    
    print(f"Response: {response.content}")
    print("Check your R4U dashboard to see the trace!")

if __name__ == "__main__":
    main()
