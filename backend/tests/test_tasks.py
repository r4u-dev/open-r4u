"""Tests for Task API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.projects import Project
from app.models.tasks import Implementation, Task


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, test_session):
    """Test creating a task."""
    payload = {
        "project": "Test Project",
        "implementation": {
            "prompt": "What is the weather like?",
            "model": "gpt-4",
            "max_output_tokens": 1000,
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
        },
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["implementation"]["prompt"] == payload["implementation"]["prompt"]
    assert data["implementation"]["model"] == payload["implementation"]["model"]
    assert data["implementation"]["tools"] is not None
    assert len(data["implementation"]["tools"]) == 1
    assert data["implementation"]["tools"][0]["type"] == "function"
    assert data["implementation"]["tools"][0]["function"]["name"] == "get_weather"
    assert (
        data["implementation"]["response_schema"]
        == payload["implementation"]["response_schema"]
    )
    assert "id" in data
    assert "project_id" in data
    assert "implementation" in data


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, test_session):
    """Test listing all tasks."""
    # Create a project
    project = Project(name="Test Project", description="Test description")
    test_session.add(project)
    await test_session.flush()

    # Create implementations
    impl1 = Implementation(
        prompt="Task 1 prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        prompt="Task 2 prompt",
        model="gpt-3.5-turbo",
        max_output_tokens=1000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.flush()

    # Create tasks
    task1 = Task(
        project_id=project.id,
        implementation_id=impl1.id,
    )
    task2 = Task(
        project_id=project.id,
        implementation_id=impl2.id,
    )
    test_session.add_all([task1, task2])
    await test_session.commit()

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    prompts = [data[0]["implementation"]["prompt"], data[1]["implementation"]["prompt"]]
    assert "Task 1 prompt" in prompts
    assert "Task 2 prompt" in prompts


@pytest.mark.asyncio
async def test_list_tasks_by_project(client: AsyncClient, test_session):
    """Test listing tasks filtered by project."""
    # Create projects
    project1 = Project(name="Project 1")
    project2 = Project(name="Project 2")
    test_session.add_all([project1, project2])
    await test_session.flush()

    # Create implementations
    impl1 = Implementation(
        prompt="Task in project 1",
        model="gpt-4",
        max_output_tokens=1000,
    )
    impl2 = Implementation(
        prompt="Task in project 2",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.flush()

    # Create tasks
    task1 = Task(
        project_id=project1.id,
        implementation_id=impl1.id,
    )
    task2 = Task(
        project_id=project2.id,
        implementation_id=impl2.id,
    )
    test_session.add_all([task1, task2])
    await test_session.commit()

    response = await client.get(f"/tasks?project_id={project1.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["implementation"]["prompt"] == "Task in project 1"
    assert data[0]["project_id"] == project1.id


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, test_session):
    """Test getting a specific task."""
    # Create a project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create implementation
    implementation = Implementation(
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=1000,
        response_schema={"type": "object"},
    )
    test_session.add(implementation)
    await test_session.flush()

    # Create task
    task = Task(
        project_id=project.id,
        implementation_id=implementation.id,
    )
    test_session.add(task)
    await test_session.commit()

    response = await client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == task.id
    assert data["implementation"]["prompt"] == "Test prompt"
    assert data["implementation"]["model"] == "gpt-4"
    assert data["implementation"]["response_schema"] == {"type": "object"}


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient):
    """Test getting a non-existent task."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, test_session):
    """Test deleting a task."""
    # Create a project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create implementation
    implementation = Implementation(
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    # Create task
    task = Task(
        project_id=project.id,
        implementation_id=implementation.id,
    )
    test_session.add(task)
    await test_session.commit()
    task_id = task.id

    # Delete the task
    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    # Verify it's deleted
    query = select(Task).where(Task.id == task_id)
    result = await test_session.execute(query)
    deleted_task = result.scalar_one_or_none()
    assert deleted_task is None


@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient):
    """Test deleting a non-existent task."""
    response = await client.delete("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_task_with_request_parameters(client: AsyncClient):
    """Test creating a task with temperature, tool_choice, and reasoning."""
    payload = {
        "project": "Test Project",
        "path": "/api/chat",
        "implementation": {
            "prompt": "What is the weather like?",
            "model": "o1-preview",
            "max_output_tokens": 2000,
            "temperature": 0.7,
            "tool_choice": "auto",
            "reasoning": {"effort": "medium", "summary": "auto"},
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
        },
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["implementation"]["prompt"] == payload["implementation"]["prompt"]
    assert data["implementation"]["model"] == payload["implementation"]["model"]
    assert (
        data["implementation"]["temperature"]
        == payload["implementation"]["temperature"]
    )
    assert data["implementation"]["tool_choice"] == {"type": "auto"}
    assert data["implementation"]["reasoning"]["effort"] == "medium"
    assert data["implementation"]["reasoning"]["summary"] == "auto"
    assert data["path"] == "/api/chat"
    assert "id" in data
