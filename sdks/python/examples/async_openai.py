"""Async example of using R4U with OpenAI."""

import asyncio
from openai import AsyncOpenAI
from r4u.integrations.openai import wrap_openai

async def main():
    """Run an async OpenAI example with tracing."""
    # Initialize async OpenAI client
    client = AsyncOpenAI()
    
    # Wrap with R4U for automatic tracing
    traced_client = wrap_openai(client, api_url="http://localhost:8000")
    
    # Make multiple concurrent chat completions - each will create a trace
    tasks = []
    questions = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms.",
        "What are the benefits of renewable energy?"
    ]
    
    for question in questions:
        task = traced_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            max_tokens=150
        )
        tasks.append(task)
    
    try:
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)
        
        for i, response in enumerate(responses):
            print(f"\nQuestion {i+1}: {questions[i]}")
            print(f"Answer: {response.choices[0].message.content}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())