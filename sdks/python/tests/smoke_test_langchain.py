"""Quick smoke test for LangChain integration."""

from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import LLMResult, ChatGeneration
from r4u.integrations.langchain import wrap_langchain


def test_langchain_integration_smoke_test():
    """Smoke test to verify the integration works end-to-end."""
    print("\n🔍 Running LangChain Integration Smoke Test...\n")
    
    # Create handler
    print("✓ Creating R4U callback handler...")
    handler = wrap_langchain(api_url="http://localhost:8000")
    
    # Mock the HTTP client
    handler._r4u_client.create_trace = Mock()
    
    # Simulate a conversation with memory
    print("✓ Simulating conversation with message history...")
    serialized = {"id": ["langchain", "chat_models", "openai", "ChatOpenAI"]}
    messages = [
        [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="My name is Alice."),
            AIMessage(content="Nice to meet you, Alice!"),
            HumanMessage(content="What's my name?"),
        ]
    ]
    
    # Start conversation
    handler.on_chat_model_start(
        serialized,
        messages,
        invocation_params={"model": "gpt-3.5-turbo"}
    )
    
    # Simulate response
    print("✓ Processing LLM response...")
    response_msg = AIMessage(content="Your name is Alice.")
    generation = ChatGeneration(message=response_msg)
    result = LLMResult(generations=[[generation]])
    
    handler.on_llm_end(result)
    
    # Verify trace was created
    print("✓ Verifying trace creation...")
    assert handler._r4u_client.create_trace.called, "Trace should have been created"
    
    call_kwargs = handler._r4u_client.create_trace.call_args[1]
    
    # Verify model
    assert call_kwargs["model"] == "gpt-3.5-turbo", "Model should be gpt-3.5-turbo"
    print(f"  ✓ Model: {call_kwargs['model']}")
    
    # Verify all input messages were captured (not the response)
    assert len(call_kwargs["messages"]) == 4, "Should have 4 input messages"
    print(f"  ✓ Messages captured: {len(call_kwargs['messages'])} input messages")
    
    # Verify message roles (input only)
    roles = [msg["role"] for msg in call_kwargs["messages"]]
    expected_roles = ["system", "user", "assistant", "user"]
    assert roles == expected_roles, f"Roles should be {expected_roles}, got {roles}"
    print(f"  ✓ Message roles: {' → '.join(roles)} (input only)")
    
    # Verify result
    assert call_kwargs["result"] == "Your name is Alice.", "Result should be the assistant's response"
    print(f"  ✓ Result: {call_kwargs['result']}")
    
    # Verify call path was captured
    assert call_kwargs["path"] is not None, "Call path should be captured"
    print(f"  ✓ Call path: {call_kwargs['path']}")
    
    print("\n✅ Smoke test passed! LangChain integration is working correctly.\n")
    print("Summary:")
    print("  • Callback handler created successfully")
    print("  • Input message history captured (4 messages)")
    print("  • Response in result field (not duplicated in messages)")
    print("  • Model name extracted correctly")
    print("  • Call path tracked")
    print("  • Trace created with all required fields")
    print("\n🎉 Integration ready for use!")


if __name__ == "__main__":
    test_langchain_integration_smoke_test()
