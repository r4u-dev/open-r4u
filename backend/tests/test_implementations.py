"""Tests for Implementation API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.tasks import Implementation


@pytest.mark.asyncio
async def test_create_implementation(client: AsyncClient, test_session):
    """Test creating an implementation."""
    payload = {
        "prompt": "What is the weather like?",
        "model": "gpt-4",
        "max_output_tokens": 1000,
        "temperature": 0.7,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ],
        "response_schema": {
            "type": "object",
            "properties": {"temperature": {"type": "number"}},
        },
    }

    response = await client.post("/implementations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["prompt"] == payload["prompt"]
    assert data["model"] == payload["model"]
    assert data["temperature"] == payload["temperature"]
    assert data["max_output_tokens"] == payload["max_output_tokens"]
    assert data["tools"] is not None
    assert len(data["tools"]) == 1
    assert data["tools"][0]["type"] == "function"
    assert data["tools"][0]["function"]["name"] == "get_weather"
    assert data["response_schema"] == payload["response_schema"]
    assert "id" in data
    assert data["version"] == "0.1"


@pytest.mark.asyncio
async def test_list_implementations(client: AsyncClient, test_session):
    """Test listing all implementations."""
    # Create implementations
    impl1 = Implementation(
        prompt="Implementation 1",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        prompt="Implementation 2",
        model="gpt-3.5-turbo",
        max_output_tokens=500,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    response = await client.get("/implementations")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    prompts = [data[0]["prompt"], data[1]["prompt"]]
    assert "Implementation 1" in prompts
    assert "Implementation 2" in prompts


@pytest.mark.asyncio
async def test_list_implementations_by_model(client: AsyncClient, test_session):
    """Test listing implementations filtered by model."""
    # Create implementations
    impl1 = Implementation(
        prompt="GPT-4 Implementation",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        prompt="GPT-3.5 Implementation",
        model="gpt-3.5-turbo",
        max_output_tokens=500,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    response = await client.get("/implementations?model=gpt-4")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["prompt"] == "GPT-4 Implementation"
    assert data[0]["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_get_implementation(client: AsyncClient, test_session):
    """Test getting a specific implementation."""
    implementation = Implementation(
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=2000,
        temperature=0.5,
        response_schema={"type": "object"},
    )
    test_session.add(implementation)
    await test_session.commit()

    response = await client.get(f"/implementations/{implementation.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == implementation.id
    assert data["prompt"] == "Test prompt"
    assert data["model"] == "gpt-4"
    assert data["max_output_tokens"] == 2000
    assert data["temperature"] == 0.5
    assert data["response_schema"] == {"type": "object"}


@pytest.mark.asyncio
async def test_get_implementation_not_found(client: AsyncClient):
    """Test getting a non-existent implementation."""
    response = await client.get("/implementations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_implementation(client: AsyncClient, test_session):
    """Test updating an implementation."""
    implementation = Implementation(
        prompt="Original prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.commit()

    # Update the implementation
    update_payload = {
        "prompt": "Updated prompt",
        "model": "gpt-4-turbo",
        "max_output_tokens": 2000,
        "temperature": 0.8,
    }
    response = await client.put(
        f"/implementations/{implementation.id}", json=update_payload
    )
    assert response.status_code == 200
    data = response.json()

    assert data["prompt"] == "Updated prompt"
    assert data["model"] == "gpt-4-turbo"
    assert data["max_output_tokens"] == 2000
    assert data["temperature"] == 0.8
    assert data["id"] == implementation.id


@pytest.mark.asyncio
async def test_delete_implementation(client: AsyncClient, test_session):
    """Test deleting an implementation."""
    implementation = Implementation(
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.commit()
    implementation_id = implementation.id

    # Delete the implementation
    response = await client.delete(f"/implementations/{implementation_id}")
    assert response.status_code == 204

    # Verify it's deleted
    query = select(Implementation).where(Implementation.id == implementation_id)
    result = await test_session.execute(query)
    deleted_implementation = result.scalar_one_or_none()
    assert deleted_implementation is None


@pytest.mark.asyncio
async def test_delete_implementation_not_found(client: AsyncClient):
    """Test deleting a non-existent implementation."""
    response = await client.delete("/implementations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_implementation_with_reasoning(client: AsyncClient):
    """Test creating an implementation with reasoning configuration."""
    payload = {
        "prompt": "Solve this problem step by step",
        "model": "o1-preview",
        "max_output_tokens": 5000,
        "reasoning": {"effort": "high", "summary": "detailed"},
        "tool_choice": {"type": "function", "function": {"name": "calculator"}},
    }

    response = await client.post("/implementations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["prompt"] == payload["prompt"]
    assert data["model"] == payload["model"]
    assert data["reasoning"]["effort"] == "high"
    assert data["reasoning"]["summary"] == "detailed"
    assert data["tool_choice"]["type"] == "function"
    assert data["tool_choice"]["function"]["name"] == "calculator"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_implementation_minimal(client: AsyncClient):
    """Test creating an implementation with only required fields."""
    payload = {
        "prompt": "Minimal implementation",
        "model": "gpt-4",
        "max_output_tokens": 100,
    }

    response = await client.post("/implementations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["prompt"] == payload["prompt"]
    assert data["model"] == payload["model"]
    assert data["max_output_tokens"] == 100
    assert data["temperature"] is None
    assert data["tools"] is None
    assert data["response_schema"] is None
    assert data["reasoning"] is None
    assert data["tool_choice"] is None
