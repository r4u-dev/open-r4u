"""Tests for Task API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.projects import Project
from app.models.tasks import Implementation, Task


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, test_session):
    """Test creating a task with initial implementation."""
    payload = {
        "project": "Test Project",
        "path": "/api/chat",
        "implementation": {
            "version": "0.1",
            "prompt": "You are a helpful assistant",
            "model": "gpt-4",
            "max_output_tokens": 1000,
            "temperature": 0.7,
        },
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["path"] == "/api/chat"
    assert data["project_id"] is not None
    assert data["production_version_id"] is not None
    assert "id" in data

    # Verify implementation was created
    impl_query = select(Implementation).where(Implementation.task_id == data["id"])
    impl_result = await test_session.execute(impl_query)
    impl = impl_result.scalar_one()

    assert impl.version == "0.1"
    assert impl.prompt == "You are a helpful assistant"
    assert impl.model == "gpt-4"
    assert impl.max_output_tokens == 1000
    assert impl.temperature == 0.7


@pytest.mark.asyncio
async def test_create_task_with_tools(client: AsyncClient, test_session):
    """Test creating a task with tools."""
    payload = {
        "project": "Test Project",
        "path": "/api/weather",
        "implementation": {
            "prompt": "Get weather information",
            "model": "gpt-4",
            "max_output_tokens": 500,
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
                },
            ],
            "tool_choice": "auto",
        },
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Verify tools were saved
    impl_query = select(Implementation).where(Implementation.task_id == data["id"])
    impl_result = await test_session.execute(impl_query)
    impl = impl_result.scalar_one()

    assert impl.tools is not None
    assert len(impl.tools) == 1
    assert impl.tools[0]["function"]["name"] == "get_weather"
    assert impl.tool_choice == {"type": "auto"}


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, test_session):
    """Test listing all tasks."""
    # Create a project
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create tasks with implementations
    task1 = Task(project_id=project.id, path="/api/chat")
    test_session.add(task1)
    await test_session.flush()

    impl1 = Implementation(
        task_id=task1.id,
        prompt="Chat assistant",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(impl1)
    await test_session.flush()

    task1.production_version_id = impl1.id

    task2 = Task(project_id=project.id, path="/api/search")
    test_session.add(task2)
    await test_session.flush()

    impl2 = Implementation(
        task_id=task2.id,
        prompt="Search assistant",
        model="gpt-3.5-turbo",
        max_output_tokens=500,
    )
    test_session.add(impl2)
    await test_session.flush()

    task2.production_version_id = impl2.id

    await test_session.commit()

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    paths = [task["path"] for task in data]
    assert "/api/chat" in paths
    assert "/api/search" in paths


@pytest.mark.asyncio
async def test_list_tasks_by_project(client: AsyncClient, test_session):
    """Test listing tasks filtered by project."""
    # Create projects
    project1 = Project(name="Project 1")
    project2 = Project(name="Project 2")
    test_session.add_all([project1, project2])
    await test_session.flush()

    # Create tasks
    task1 = Task(project_id=project1.id, path="/api/v1")
    task2 = Task(project_id=project2.id, path="/api/v2")
    test_session.add_all([task1, task2])
    await test_session.flush()

    impl1 = Implementation(
        task_id=task1.id, prompt="V1", model="gpt-4", max_output_tokens=1000,
    )
    impl2 = Implementation(
        task_id=task2.id, prompt="V2", model="gpt-4", max_output_tokens=1000,
    )
    test_session.add_all([impl1, impl2])
    await test_session.flush()

    task1.production_version_id = impl1.id
    task2.production_version_id = impl2.id
    await test_session.commit()

    response = await client.get(f"/tasks?project_id={project1.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["path"] == "/api/v1"
    assert data[0]["project_id"] == project1.id


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, test_session):
    """Test getting a specific task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id, path="/api/test")
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="Test prompt",
        model="gpt-4",
        max_output_tokens=2000,
        response_schema={"type": "object"},
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    await test_session.commit()

    response = await client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == task.id
    assert data["path"] == "/api/test"
    assert data["production_version_id"] == implementation.id


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient):
    """Test getting a non-existent task."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, test_session):
    """Test deleting a task (should cascade delete implementations)."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id, path="/api/test")
    test_session.add(task)
    await test_session.flush()

    implementation = Implementation(
        task_id=task.id,
        prompt="Test",
        model="gpt-4",
        max_output_tokens=1000,
    )
    test_session.add(implementation)
    await test_session.flush()

    task.production_version_id = implementation.id
    await test_session.commit()

    task_id = task.id
    impl_id = implementation.id

    # Delete the task
    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    # Verify task is deleted
    task_query = select(Task).where(Task.id == task_id)
    task_result = await test_session.execute(task_query)
    deleted_task = task_result.scalar_one_or_none()
    assert deleted_task is None

    # Verify implementation is also deleted (cascade)
    impl_query = select(Implementation).where(Implementation.id == impl_id)
    impl_result = await test_session.execute(impl_query)
    deleted_impl = impl_result.scalar_one_or_none()
    assert deleted_impl is None


@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient):
    """Test deleting a non-existent task."""
    response = await client.delete("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_task_with_reasoning(client: AsyncClient):
    """Test creating a task with reasoning configuration."""
    payload = {
        "project": "Test Project",
        "path": "/api/reason",
        "implementation": {
            "prompt": "Solve this problem",
            "model": "o1-preview",
            "max_output_tokens": 5000,
            "reasoning": {"effort": "high", "summary": "detailed"},
            "temperature": 1.0,
        },
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["path"] == "/api/reason"
    assert data["production_version_id"] is not None
