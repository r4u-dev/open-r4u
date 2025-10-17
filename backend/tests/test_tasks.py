"""Tests for Task API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.projects import Project
from app.models.tasks import Task


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, test_session):
    """Test creating a task."""
    payload = {
        "project": "Test Project",
        "prompt": "What is the weather like?",
        "model": "gpt-4",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    }
                }
            }
        ],
        "response_schema": {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"}
            }
        }
    }

    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["prompt"] == payload["prompt"]
    assert data["model"] == payload["model"]
    assert data["tools"] is not None
    assert len(data["tools"]) == 1
    assert data["tools"][0]["type"] == "function"
    assert data["tools"][0]["function"]["name"] == "get_weather"
    assert data["response_schema"] == payload["response_schema"]
    assert "id" in data
    assert "project_id" in data


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, test_session):
    """Test listing all tasks."""
    # Create a project
    project = Project(name="Test Project", description="Test description")
    test_session.add(project)
    await test_session.flush()

    # Create tasks
    task1 = Task(
        project_id=project.id,
        prompt="Task 1 prompt",
        model="gpt-4",
        tools=None,
        response_schema=None,
    )
    task2 = Task(
        project_id=project.id,
        prompt="Task 2 prompt",
        model="gpt-3.5-turbo",
        tools=None,
        response_schema=None,
    )
    test_session.add_all([task1, task2])
    await test_session.commit()

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["prompt"] in ["Task 1 prompt", "Task 2 prompt"]
    assert data[1]["prompt"] in ["Task 1 prompt", "Task 2 prompt"]


@pytest.mark.asyncio
async def test_list_tasks_by_project(client: AsyncClient, test_session):
    """Test listing tasks filtered by project."""
    # Create projects
    project1 = Project(name="Project 1")
    project2 = Project(name="Project 2")
    test_session.add_all([project1, project2])
    await test_session.flush()

    # Create tasks
    task1 = Task(
        project_id=project1.id,
        prompt="Task in project 1",
        model="gpt-4",
    )
    task2 = Task(
        project_id=project2.id,
        prompt="Task in project 2",
        model="gpt-4",
    )
    test_session.add_all([task1, task2])
    await test_session.commit()

    response = await client.get(f"/tasks?project_id={project1.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["prompt"] == "Task in project 1"
    assert data[0]["project_id"] == project1.id


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, test_session):
    """Test getting a specific task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        project_id=project.id,
        prompt="Test prompt",
        model="gpt-4",
        tools=None,
        response_schema={"type": "object"},
    )
    test_session.add(task)
    await test_session.commit()

    response = await client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == task.id
    assert data["prompt"] == "Test prompt"
    assert data["model"] == "gpt-4"
    assert data["response_schema"] == {"type": "object"}


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient):
    """Test getting a non-existent task."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, test_session):
    """Test updating a task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        project_id=project.id,
        prompt="Original prompt",
        model="gpt-4",
    )
    test_session.add(task)
    await test_session.commit()

    # Update the task
    update_payload = {
        "prompt": "Updated prompt",
        "model": "gpt-4-turbo",
    }
    response = await client.patch(f"/tasks/{task.id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["prompt"] == "Updated prompt"
    assert data["model"] == "gpt-4-turbo"
    assert data["id"] == task.id


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, test_session):
    """Test deleting a task."""
    # Create a project and task
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(
        project_id=project.id,
        prompt="Test prompt",
        model="gpt-4",
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
