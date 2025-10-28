"""Test HTTP trace ingestion."""

import json
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_openai_http_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from OpenAI HTTP request/response."""
    # Sample OpenAI request
    request_data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "temperature": 0.7,
    }

    # Sample OpenAI response
    response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The capital of France is Paris.",
                },
                "finish_reason": "stop",
            },
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
            "host": "api.openai.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://api.openai.com/v1/chat/completions",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/v1/http-traces", json=payload)

    if response.status_code != 201:
        print(f"Error: {response.status_code}")
        print(f"Detail: {response.json()}")

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "gpt-4"
    assert data["result"] == "The capital of France is Paris."
    assert data["temperature"] == 0.7
    assert data["prompt_tokens"] == 20
    assert data["completion_tokens"] == 10
    assert data["total_tokens"] == 30
    assert data["finish_reason"] == "stop"

    # Verify input items were created
    assert len(data["input"]) == 2
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "system"
    assert data["input"][1]["data"]["role"] == "user"


@pytest.mark.asyncio
async def test_create_anthropic_http_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from Anthropic HTTP request/response."""
    # Sample Anthropic request
    request_data = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1024,
        "system": "You are a helpful assistant.",
        "messages": [
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "temperature": 0.7,
    }

    # Sample Anthropic response
    response_data = {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "The capital of France is Paris.",
            },
        ],
        "model": "claude-3-opus-20240229",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 20,
            "output_tokens": 10,
        },
    }

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "x-api-key": "sk-test",
            "host": "api.anthropic.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://api.anthropic.com/v1/messages",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/v1/http-traces", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "claude-3-opus-20240229"
    assert data["result"] == "The capital of France is Paris."
    assert data["temperature"] == 0.7
    assert data["prompt_tokens"] == 20
    assert data["completion_tokens"] == 10
    assert data["total_tokens"] == 30
    assert data["finish_reason"] == "stop"
    assert data["instructions"] == "You are a helpful assistant."

    # Verify input items were created (should have system message + user message)
    assert len(data["input"]) == 2
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "system"
    assert data["input"][1]["data"]["role"] == "user"


@pytest.mark.asyncio
async def test_create_openai_responses_api_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from OpenAI Responses API format."""
    # Sample OpenAI Responses API request
    request_data = {
        "model": "gpt-4",
        "input": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ],
        "temperature": 0.7,
    }

    # Sample OpenAI Responses API response
    response_data = {
        "id": "resp-123",
        "object": "response",
        "created": 1677652288,
        "model": "gpt-4",
        "output": "The capital of France is Paris.",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
            "host": "api.openai.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/v1/http-traces", json=payload)

    if response.status_code != 201:
        print(f"Error: {response.status_code}")
        print(f"Detail: {response.json()}")

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "gpt-4"
    assert data["result"] == "The capital of France is Paris."
    assert data["temperature"] == 0.7
    assert data["prompt_tokens"] == 20
    assert data["completion_tokens"] == 10
    assert data["total_tokens"] == 30
    assert data["finish_reason"] == "stop"

    # Verify input items were created
    assert len(data["input"]) == 2
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "system"
    assert data["input"][1]["data"]["role"] == "user"


@pytest.mark.asyncio
async def test_unsupported_provider(client: AsyncClient, test_session: AsyncSession):
    """Test that unsupported provider returns error."""
    request_data = {"test": "data"}
    response_data = {"result": "data"}

    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "host": "unsupported-provider.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://unsupported-provider.com/v1/api",
            "method": "POST",
        },
    }

    response = await client.post("/v1/http-traces", json=payload)

    assert response.status_code == 400
    assert "No parser found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_openai_tool_call_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from OpenAI with tool calls."""
    # Sample OpenAI request with tools
    request_data = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            },
        ],
        "temperature": 0.7,
    }

    # Sample OpenAI response with tool call
    response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "San Francisco"}',
                            },
                        },
                    ],
                },
                "finish_reason": "tool_calls",
            },
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
    }

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
            "host": "api.openai.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://api.openai.com/v1/chat/completions",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/v1/http-traces", json=payload)

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "gpt-4"
    assert data["result"] is None  # No content for tool calls
    assert data["temperature"] == 0.7
    assert data["prompt_tokens"] == 50
    assert data["completion_tokens"] == 20
    assert data["total_tokens"] == 70
    assert data["finish_reason"] == "tool_calls"

    # Verify input items were created
    assert len(data["input"]) == 2
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "user"
    assert data["input"][1]["type"] == "tool_call"

    # Verify tool calls were created
    assert data["input"][1]["data"]["tool_name"] == "get_weather"
    assert data["input"][1]["data"]["arguments"] == {"location": "San Francisco"}


@pytest.mark.asyncio
async def test_http_trace_persisted_on_parse_failure(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test that HTTPTrace is persisted even when parsing fails."""
    from sqlalchemy import select

    from app.models.http_traces import HTTPTrace
    from app.models.traces import Trace

    # Create a payload that will fail to parse (unsupported provider)
    request_data = {"test": "data"}
    response_data = {"result": "data"}

    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "host": "unknown-provider.com",
        },
        "response": json.dumps(response_data).encode("utf-8").hex(),
        "response_headers": {
            "content-type": "application/json",
        },
        "metadata": {
            "url": "https://unknown-provider.com/v1/api",
            "method": "POST",
            "project": "Test Project",
        },
    }

    # Send the request - should fail with 400
    response = await client.post("/v1/http-traces", json=payload)
    assert response.status_code == 400
    assert "No parser found" in response.json()["detail"]

    # Verify HTTPTrace was still saved to the database
    http_trace_query = select(HTTPTrace).order_by(HTTPTrace.id.desc()).limit(1)
    result = await test_session.execute(http_trace_query)
    http_trace = result.scalar_one_or_none()

    assert http_trace is not None
    assert http_trace.status_code == 200
    assert "unknown-provider.com" in http_trace.request_headers["host"]
    assert json.loads(http_trace.request) == request_data
    assert json.loads(http_trace.response) == response_data

    # Verify no Trace was created (because parsing failed)
    trace_query = select(Trace).where(Trace.http_trace_id == http_trace.id)
    trace_result = await test_session.execute(trace_query)
    trace = trace_result.scalar_one_or_none()

    assert trace is None, "No Trace should be created when parsing fails"


@pytest.mark.asyncio
async def test_create_openai_streaming_chat_completions_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from OpenAI streaming Chat Completions API."""
    # Sample OpenAI request
    request_data = {
        "model": "gpt-3.5-turbo-0125",
        "messages": [
            {"role": "user", "content": "Say hi"},
        ],
        "stream": True,
    }

    # Sample OpenAI streaming response (chunks concatenated with \n\n)
    streaming_response = """data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"role":"assistant","content":"","refusal":null},"logprobs":null,"finish_reason":null}],"obfuscation":"kSx18"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":"Hi"},"logprobs":null,"finish_reason":null}],"obfuscation":"Gpkah"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":","},"logprobs":null,"finish_reason":null}],"obfuscation":"38dLw0"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":" how"},"logprobs":null,"finish_reason":null}],"obfuscation":"M5w"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":" are"},"logprobs":null,"finish_reason":null}],"obfuscation":"AKb"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":" you"},"logprobs":null,"finish_reason":null}],"obfuscation":"e8E"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{"content":"?"},"logprobs":null,"finish_reason":null}],"obfuscation":"2c6Xq1"}

data: {"id":"chatcmpl-CVFjOTBIgA3kuQLnIXXxtg7Ge7hbs","object":"chat.completion.chunk","created":1761564674,"model":"gpt-3.5-turbo-0125","service_tier":"default","system_fingerprint":null,"choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}],"obfuscation":"a"}

data: [DONE]"""

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
            "host": "api.openai.com",
        },
        "response": streaming_response.encode("utf-8").hex(),
        "response_headers": {
            "content-type": "text/event-stream",
        },
        "metadata": {
            "url": "https://api.openai.com/v1/chat/completions",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/http-traces", json=payload)

    if response.status_code != 201:
        print(f"Error: {response.status_code}")
        print(f"Detail: {response.json()}")

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "gpt-3.5-turbo-0125"
    assert data["result"] == "Hi, how are you?"
    assert data["finish_reason"] == "stop"

    # Verify input items were created
    assert len(data["input"]) == 1
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "user"


@pytest.mark.asyncio
async def test_create_openai_streaming_responses_api_trace(
    client: AsyncClient,
    test_session: AsyncSession,
):
    """Test creating a trace from OpenAI streaming Responses API."""
    # Sample OpenAI Responses API request
    request_data = {
        "model": "gpt-3.5-turbo-0125",
        "input": [
            {"role": "user", "content": "Say some greetings"},
        ],
        "stream": True,
    }

    # Sample OpenAI Responses API streaming response (chunks concatenated with \n\n)
    streaming_response = """event: response.created
data: {"type":"response.created","sequence_number":0,"response":{"id":"resp_045d5195f1ed9f940068ff5b16458c8197acc79be8346cd880","object":"response","created_at":1761565462,"status":"in_progress","background":false,"error":null,"incomplete_details":null,"instructions":null,"max_output_tokens":null,"max_tool_calls":null,"model":"gpt-3.5-turbo-0125","output":[],"parallel_tool_calls":true,"previous_response_id":null,"prompt_cache_key":null,"reasoning":{"effort":null,"summary":null},"safety_identifier":null,"service_tier":"auto","store":true,"temperature":1.0,"text":{"format":{"type":"text"},"verbosity":"medium"},"tool_choice":"auto","tools":[],"top_logprobs":0,"top_p":1.0,"truncation":"disabled","usage":null,"user":null,"metadata":{}}}

event: response.in_progress
data: {"type":"response.in_progress","sequence_number":1,"response":{"id":"resp_045d5195f1ed9f940068ff5b16458c8197acc79be8346cd880","object":"response","created_at":1761565462,"status":"in_progress","background":false,"error":null,"incomplete_details":null,"instructions":null,"max_output_tokens":null,"max_tool_calls":null,"model":"gpt-3.5-turbo-0125","output":[],"parallel_tool_calls":true,"previous_response_id":null,"prompt_cache_key":null,"reasoning":{"effort":null,"summary":null},"safety_identifier":null,"service_tier":"auto","store":true,"temperature":1.0,"text":{"format":{"type":"text"},"verbosity":"medium"},"tool_choice":"auto","tools":[],"top_logprobs":0,"top_p":1.0,"truncation":"disabled","usage":null,"user":null,"metadata":{}}}

event: response.output_item.added
data: {"type":"response.output_item.added","sequence_number":2,"output_index":0,"item":{"id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","type":"message","status":"in_progress","content":[],"role":"assistant"}}

event: response.content_part.added
data: {"type":"response.content_part.added","sequence_number":3,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"part":{"type":"output_text","annotations":[],"logprobs":[],"text":""}}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":4,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":"Greetings","logprobs":[],"obfuscation":"mvkAadO"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":5,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":",","logprobs":[],"obfuscation":"d3983J1LnnINX8U"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":6,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":" hello","logprobs":[],"obfuscation":"TZOE4wuLRN"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":7,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":",","logprobs":[],"obfuscation":"1IgEZnLm4x3wykQ"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":8,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":" hi","logprobs":[],"obfuscation":"OUVlhaiOQDTgm"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":9,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":",","logprobs":[],"obfuscation":"1VMNe9emr6FMPYR"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":10,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":" hey","logprobs":[],"obfuscation":"CDv4Vfns9WCh"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":11,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":",","logprobs":[],"obfuscation":"qYiIWF51l1Q0QPz"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":12,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":" sal","logprobs":[],"obfuscation":"V1VCdyRXwMpb"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":13,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":"utations","logprobs":[],"obfuscation":"8KyjANpr"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","sequence_number":14,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"delta":"!","logprobs":[],"obfuscation":"WraPeSlOcUXTOJ2"}

event: response.output_text.done
data: {"type":"response.output_text.done","sequence_number":15,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"text":"Greetings, hello, hi, hey, salutations!","logprobs":[]}

event: response.content_part.done
data: {"type":"response.content_part.done","sequence_number":16,"item_id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","output_index":0,"content_index":0,"part":{"type":"output_text","annotations":[],"logprobs":[],"text":"Greetings, hello, hi, hey, salutations!"}}

event: response.output_item.done
data: {"type":"response.output_item.done","sequence_number":17,"output_index":0,"item":{"id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","type":"message","status":"completed","content":[{"type":"output_text","annotations":[],"logprobs":[],"text":"Greetings, hello, hi, hey, salutations!"}],"role":"assistant"}}

event: response.completed
data: {"type":"response.completed","sequence_number":18,"response":{"id":"resp_045d5195f1ed9f940068ff5b16458c8197acc79be8346cd880","object":"response","created_at":1761565462,"status":"completed","background":false,"error":null,"incomplete_details":null,"instructions":null,"max_output_tokens":null,"max_tool_calls":null,"model":"gpt-3.5-turbo-0125","output":[{"id":"msg_045d5195f1ed9f940068ff5b17fd08819787a7a968fc33300f","type":"message","status":"completed","content":[{"type":"output_text","annotations":[],"logprobs":[],"text":"Greetings, hello, hi, hey, salutations!"}],"role":"assistant"}],"parallel_tool_calls":true,"previous_response_id":null,"prompt_cache_key":null,"reasoning":{"effort":null,"summary":null},"safety_identifier":null,"service_tier":"default","store":true,"temperature":1.0,"text":{"format":{"type":"text"},"verbosity":"medium"},"tool_choice":"auto","tools":[],"top_logprobs":0,"top_p":1.0,"truncation":"disabled","usage":{"input_tokens":13,"input_tokens_details":{"cached_tokens":0},"output_tokens":12,"output_tokens_details":{"reasoning_tokens":0},"total_tokens":25},"user":null,"metadata":{}}}"""

    # Create HTTP trace payload
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)

    payload = {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status_code": 200,
        "error": None,
        "request": json.dumps(request_data).encode("utf-8").hex(),
        "request_headers": {
            "content-type": "application/json",
            "authorization": "Bearer sk-test",
            "host": "api.openai.com",
        },
        "response": streaming_response.encode("utf-8").hex(),
        "response_headers": {
            "content-type": "text/event-stream",
        },
        "metadata": {
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "project": "Test Project",
        },
    }

    response = await client.post("/http-traces", json=payload)

    if response.status_code != 201:
        print(f"Error: {response.status_code}")
        print(f"Detail: {response.json()}")

    assert response.status_code == 201
    data = response.json()

    # Verify trace was created correctly
    assert data["model"] == "gpt-3.5-turbo-0125"
    assert data["result"] == "Greetings, hello, hi, hey, salutations!"
    assert data["temperature"] == 1.0
    assert data["prompt_tokens"] == 13
    assert data["completion_tokens"] == 12
    assert data["total_tokens"] == 25

    # Verify input items were created
    assert len(data["input"]) == 1
    assert data["input"][0]["type"] == "message"
    assert data["input"][0]["data"]["role"] == "user"
