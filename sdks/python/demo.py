#!/usr/bin/env python3
"""Demo script showing R4U SDK functionality."""

import asyncio
from datetime import datetime
from r4u.client import R4UClient


async def demo_manual_tracing():
    """Demonstrate manual trace creation."""
    print("=== Manual Tracing Demo ===")
    
    client = R4UClient(api_url="http://localhost:8000")
    
    try:
        # Create a manual trace
        trace = await client.create_trace_async(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2 + 2?"},
                {"role": "assistant", "content": "2 + 2 equals 4."}
            ],
            result="2 + 2 equals 4.",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        print(f"Created trace with ID: {trace.id}")
        print(f"Model: {trace.model}")
        print(f"Messages: {len(trace.messages)}")
        print(f"Result: {trace.result}")
        
    except Exception as e:
        print(f"Error creating trace: {e}")
    
    try:
        # List all traces
        traces = await client.list_traces_async()
        print(f"\nTotal traces in system: {len(traces)}")
        
        if traces:
            latest_trace = traces[-1]
            print(f"Latest trace ID: {latest_trace.id}")
            print(f"Latest trace model: {latest_trace.model}")
        
    except Exception as e:
        print(f"Error listing traces: {e}")
    
    await client.close()


def demo_openai_integration():
    """Demonstrate OpenAI integration (requires OpenAI library)."""
    print("\n=== OpenAI Integration Demo ===")
    
    try:
        from openai import OpenAI
        from r4u.integrations.openai import wrap_openai
        
        print("Setting up OpenAI client with R4U tracing...")
        
        # Initialize OpenAI client
        client = OpenAI()
        
        # Wrap with R4U for automatic tracing
        traced_client = wrap_openai(client, api_url="http://localhost:8000")
        
        print("✓ OpenAI client wrapped successfully!")
        
        # Make a simple completion call
        print("\nMaking OpenAI API call...")
        print("Question: What is the capital of France?")
        
        response = traced_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France? Please answer in one sentence."}
            ],
            max_tokens=50
        )
        
        answer = response.choices[0].message.content
        print(f"Answer: {answer}")
        print("✓ API call completed successfully!")
        print("✓ Trace should be automatically created in R4U system")
        
        # Verify trace was created by listing traces
        print("\nVerifying trace creation...")
        try:
            from r4u.client import R4UClient
            r4u_client = R4UClient(api_url="http://localhost:8000")
            traces = r4u_client.list_traces()
            
            print(f"Total traces in system: {len(traces)}")
            
            if traces:
                # Sort traces by ID to get the most recent one
                traces_by_id = sorted(traces, key=lambda t: t.id)
                latest_trace = traces_by_id[-1]
                
                print(f"✓ Latest trace ID: {latest_trace.id}")
                print(f"  Model: {latest_trace.model}")
                print(f"  Messages: {len(latest_trace.messages)}")
                
                if latest_trace.path:
                    print(f"  Call Path: {latest_trace.path}")
                else:
                    print("  Call Path: Not captured")
                
                if latest_trace.result:
                    preview = latest_trace.result[:100] + "..." if len(latest_trace.result) > 100 else latest_trace.result
                    print(f"  Result: {preview}")
                else:
                    print("  No result captured")
                
                # Count OpenAI traces to show integration is working
                openai_traces = [t for t in traces if t.model == "gpt-3.5-turbo"]
                print(f"✓ Found {len(openai_traces)} traces with gpt-3.5-turbo model")
                
            else:
                print("! No traces found - check if R4U API is running")
                
        except Exception as trace_error:
            print(f"! Could not verify trace creation: {trace_error}")
        
    except ImportError:
        print("OpenAI library not installed. Install with: pip install openai")
    except Exception as e:
        print(f"Error in OpenAI integration demo: {e}")
        print("Make sure OPENAI_API_KEY is set and R4U API is running at http://localhost:8000")


async def main():
    """Run all demos."""
    print("R4U SDK Demo")
    print("============")
    print("Make sure your R4U API server is running at http://localhost:8000")
    print()
    
    await demo_manual_tracing()
    demo_openai_integration()
    
    print("\nDemo complete!")


if __name__ == "__main__":
    asyncio.run(main())