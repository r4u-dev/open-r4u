"""Basic example of using R4U with OpenAI synchronously."""

from openai import OpenAI
from r4u.integrations.openai import wrap_openai

def main():
    """Run a basic OpenAI example with tracing."""
    # Initialize OpenAI client
    client = OpenAI()
    
    # Wrap with R4U for automatic tracing
    traced_client = wrap_openai(client, api_url="http://localhost:8000")
    
    # Make a simple chat completion - this will automatically create a trace
    try:
        response = traced_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"}
            ],
            max_tokens=100
        )
        
        print("Response:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()