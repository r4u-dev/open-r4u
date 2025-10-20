"""Example usage of R4U Google GenAI integration."""

import os
from r4u.integrations.google_genai import GenerativeModel

# Set your Google API key
# os.environ["GOOGLE_API_KEY"] = "your-api-key-here"

def main():
    """Example of using Google GenAI with R4U tracing."""
    
    # Initialize the model with tracing
    model = GenerativeModel('gemini-1.5-pro')
    
    # Generate content - this will be automatically traced
    response = model.generate_content("What is the capital of France?")
    
    print(f"Response: {response.text}")
    print("Check your R4U dashboard to see the trace!")

if __name__ == "__main__":
    main()
