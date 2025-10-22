"""Test HTTP trace ingestion."""

import json
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_openai_http_trace(client: AsyncClient, test_session: AsyncSession):
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

    response = await client.post("/http-traces", json=payload)

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
async def test_create_anthropic_http_trace(client: AsyncClient, test_session: AsyncSession):
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

    response = await client.post("/http-traces", json=payload)

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
async def test_create_openai_responses_api_trace(client: AsyncClient, test_session: AsyncSession):
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

    response = await client.post("/http-traces", json=payload)

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

    response = await client.post("/http-traces", json=payload)

    assert response.status_code == 400
    assert "No parser found" in response.json()["detail"]
