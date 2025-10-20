"""Example usage of R4U LangChain Google GenAI integration."""

import os
from r4u.tracing.langchain.google_genai import ChatGoogleGenerativeAI

# Set your Google API key
# os.environ["GOOGLE_API_KEY"] = "your-api-key-here"

def main():
    """Example of using LangChain Google GenAI with R4U tracing."""
    
    # Initialize the model with tracing
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
    
    # Generate content - this will be automatically traced
    response = llm.invoke("What is the capital of France?")
    
    print(f"Response: {response.content}")
    print("Check your R4U dashboard to see the trace!")

if __name__ == "__main__":
    main()
