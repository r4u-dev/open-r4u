"""Tests for Implementation API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.projects import Project
from app.models.providers import Model, Provider
from app.models.tasks import Implementation, Task


@pytest.mark.asyncio
async def test_create_implementation_for_task(client: AsyncClient, test_session):
    """Test creating an implementation version for a task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.commit()

    # Create implementation
    payload = {
        "version": "1.0",
        "prompt": "You are a helpful assistant",
        "model": "openai/gpt-4",
        "max_output_tokens": 2000,
        "temperature": 0.7,
    }

    response = await client.post(f"/v1/implementations?task_id={task.id}", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["task_id"] == task.id
    assert data["version"] == "1.0"
    assert data["prompt"] == "You are a helpful assistant"
    assert data["model"] == "openai/gpt-4"
    assert data["max_output_tokens"] == 2000
    assert data["temperature"] == 0.7
    assert "id" in data


@pytest.mark.asyncio
async def test_create_implementation_for_nonexistent_task(client: AsyncClient):
    """Test creating an implementation for a task that doesn't exist."""
    payload = {
        "prompt": "Test",
        "model": "openai/gpt-4",
        "max_output_tokens": 1000,
    }

    response = await client.post("/v1/implementations?task_id=99999", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_implementations_by_task(client: AsyncClient, test_session):
    """Test listing implementations for a specific task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.flush()

    # Create multiple implementations
    impl1 = Implementation(
        task_id=task.id,
        version="1.0",
        prompt="Version 1",
        model="openai/gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task.id,
        version="1.1",
        prompt="Version 1.1",
        model="openai/gpt-4",
        max_output_tokens=1500,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    response = await client.get(f"/v1/implementations?task_id={task.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    versions = [impl["version"] for impl in data]
    assert "1.0" in versions
    assert "1.1" in versions


@pytest.mark.asyncio
async def test_list_all_implementations(client: AsyncClient, test_session):
    """Test listing all implementations across tasks."""
    # Create a project and tasks
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task1 = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/task1",
    )
    task2 = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/task2",
    )
    test_session.add_all([task1, task2])
    await test_session.flush()

    # Create implementations for different tasks
    impl1 = Implementation(
        task_id=task1.id,
        prompt="Task 1 impl",
        model="openai/gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task2.id,
        prompt="Task 2 impl",
        model="openai/gpt-3.5-turbo",
        max_output_tokens=500,
    )
    test_session.add_all([impl1, impl2])
    await test_session.commit()

    response = await client.get("/v1/implementations")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    task_ids = [impl["task_id"] for impl in data]
    assert task1.id in task_ids
    assert task2.id in task_ids


@pytest.mark.asyncio
async def test_get_implementation(client: AsyncClient, test_session):
    """Test getting a specific implementation."""
    # Create a project, task, and implementation
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        version="2.0",
        prompt="Test prompt",
        model="openai/gpt-4-turbo",
        max_output_tokens=3000,
        temperature=0.5,
    )
    test_session.add(implementation)
    await test_session.commit()

    response = await client.get(f"/v1/implementations/{implementation.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == implementation.id
    assert data["task_id"] == task.id
    assert data["version"] == "2.0"
    assert data["prompt"] == "Test prompt"
    assert data["model"] == "openai/gpt-4-turbo"
    assert data["max_output_tokens"] == 3000
    assert data["temperature"] == 0.5
    # response_schema is no longer part of implementation


@pytest.mark.asyncio
async def test_get_implementation_not_found(client: AsyncClient):
    """Test getting a non-existent implementation."""
    response = await client.get("/v1/implementations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_implementation(client: AsyncClient, test_session):
    """Test updating an implementation."""
    # Set up providers and models for canonicalization
    provider = Provider(name="openai", display_name="OpenAI")
    test_session.add(provider)
    await test_session.flush()

    model1 = Model(provider_id=provider.id, name="gpt-4", display_name="GPT-4")
    model2 = Model(
        provider_id=provider.id,
        name="gpt-4-turbo",
        display_name="GPT-4 Turbo",
    )
    test_session.add_all([model1, model2])
    await test_session.flush()

    # Create a project, task, and implementation
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        version="1.0",
        prompt="Original prompt",
        model="openai/gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.commit()

    # Update the implementation
    update_payload = {
        "prompt": "Updated prompt",
    }
    response = await client.put(
        f"/v1/implementations/{implementation.id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["prompt"] == "Updated prompt"


@pytest.mark.asyncio
async def test_delete_implementation(client: AsyncClient, test_session):
    """Test deleting an implementation."""
    # Create a project, task, and implementation
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="openai/gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.commit()
    implementation_id = implementation.id

    # Delete the implementation
    response = await client.delete(f"/v1/implementations/{implementation_id}")
    assert response.status_code == 204

    # Verify it's deleted
    query = select(Implementation).where(Implementation.id == implementation_id)
    result = await test_session.execute(query)
    deleted_implementation = result.scalar_one_or_none()
    assert deleted_implementation is None


@pytest.mark.asyncio
async def test_delete_implementation_not_found(client: AsyncClient):
    """Test deleting a non-existent implementation."""
    response = await client.delete("/v1/implementations/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_set_production_version(client: AsyncClient, test_session):
    """Test setting an implementation as the production version."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/test",
    )
    test_session.add(task)
    await test_session.flush()

    # Create multiple implementations
    impl1 = Implementation(
        task_id=task.id,
        version="1.0",
        prompt="Version 1",
        model="openai/gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task.id,
        version="2.0",
        prompt="Version 2",
        model="openai/gpt-4",
        max_output_tokens=2000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.flush()

    # Set first as production
    task.production_version_id = impl1.id
    await test_session.commit()

    # Now set second as production via API
    response = await client.post(f"/v1/implementations/{impl2.id}/set-production")
    assert response.status_code == 200

    # Verify task's production version was updated
    await test_session.refresh(task)
    assert task.production_version_id == impl2.id


@pytest.mark.asyncio
async def test_set_production_version_not_found(client: AsyncClient):
    """Test setting production version for non-existent implementation."""
    response = await client.post("/v1/implementations/99999/set-production")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_implementation_with_tools(client: AsyncClient, test_session):
    """Test creating an implementation with tools configuration."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/weather",
    )
    test_session.add(task)
    await test_session.commit()

    payload = {
        "prompt": "Get weather information",
        "model": "gpt-4",
        "max_output_tokens": 1500,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            },
        ],
        "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
    }

    response = await client.post(f"/v1/implementations?task_id={task.id}", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["tools"] is not None
    assert len(data["tools"]) == 1
    assert data["tools"][0]["function"]["name"] == "get_weather"
    assert data["tool_choice"]["type"] == "function"


@pytest.mark.asyncio
async def test_create_implementation_with_reasoning(client: AsyncClient, test_session):
    """Test creating an implementation with reasoning configuration."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/reason",
    )
    test_session.add(task)
    await test_session.commit()

    payload = {
        "prompt": "Solve this problem step by step",
        "model": "openai/o1-preview",
        "max_output_tokens": 5000,
        "reasoning": {"effort": "high", "summary": "detailed"},
    }

    response = await client.post(f"/v1/implementations?task_id={task.id}", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["reasoning"] is not None
    assert data["reasoning"]["effort"] == "high"
    assert data["reasoning"]["summary"] == "detailed"


@pytest.mark.asyncio
async def test_multiple_versions_for_task(client: AsyncClient, test_session):
    """Test creating multiple versions of implementations for the same task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        name="Test Task",
        description="Test task",
        project_id=project.id,
        path="/api/chat",
    )
    test_session.add(task)
    await test_session.commit()

    # Create multiple versions
    versions = ["0.1", "0.2", "1.0", "1.1"]
    for version in versions:
        payload = {
            "version": version,
            "prompt": f"Version {version} prompt",
            "model": "gpt-4",
            "max_output_tokens": 1000,
        }
        response = await client.post(
            f"/v1/implementations?task_id={task.id}",
            json=payload,
        )
        assert response.status_code == 201

    # List all versions for this task
    response = await client.get(f"/v1/implementations?task_id={task.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 4
    returned_versions = [impl["version"] for impl in data]
    for version in versions:
        assert version in returned_versions
