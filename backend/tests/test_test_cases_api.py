"""Tests for test cases API endpoints."""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select

from app.models.evaluation import TestCase
from app.models.projects import Project
from app.models.tasks import Task


@pytest.mark.asyncio
async def test_create_test_case(client: AsyncClient, test_session):
    """Test creating a test case via API."""
    # Create project and task first
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "description": "Test case for accuracy",
        "arguments": {"input": "What is 2+2?", "user_id": "123"},
        "expected_output": "4"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["description"] == "Test case for accuracy"
    assert data["arguments"] == {"input": "What is 2+2?", "user_id": "123"}
    assert data["expected_output"] == "4"
    assert data["task_id"] == task.id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify test case was created in database
    test_case_query = select(TestCase).where(TestCase.id == data["id"])
    test_case_result = await test_session.execute(test_case_query)
    test_case = test_case_result.scalar_one()
    
    assert test_case.description == "Test case for accuracy"
    assert test_case.arguments == {"input": "What is 2+2?", "user_id": "123"}
    assert test_case.expected_output == "4"


@pytest.mark.asyncio
async def test_create_test_case_minimal(client: AsyncClient, test_session):
    """Test creating a test case with minimal required fields."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "expected_output": "Expected result"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["description"] is None
    assert data["arguments"] is None
    assert data["expected_output"] == "Expected result"
    assert data["task_id"] == task.id


@pytest.mark.asyncio
async def test_create_test_case_task_not_found(client: AsyncClient):
    """Test creating a test case for non-existent task."""
    payload = {
        "description": "Test case",
        "expected_output": "Expected result"
    }

    response = await client.post("/test-cases/tasks/999/test-cases", json=payload)
    assert response.status_code == 404
    
    data = response.json()
    assert "Task with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_create_test_case_validation_error(client: AsyncClient, test_session):
    """Test creating a test case with validation errors."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "description": "Test case",
        # Missing required expected_output
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_test_cases(client: AsyncClient, test_session):
    """Test listing test cases for a task."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    # Create test cases
    test_case1 = TestCase(
        task_id=task.id,
        description="Test case 1",
        arguments={"input": "test1"},
        expected_output="expected1",
    )
    test_session.add(test_case1)

    test_case2 = TestCase(
        task_id=task.id,
        description="Test case 2",
        arguments={"input": "test2"},
        expected_output="expected2",
    )
    test_session.add(test_case2)

    await test_session.commit()

    response = await client.get(f"/test-cases/tasks/{task.id}/test-cases")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    
    # Check that both test cases are present
    descriptions = [tc["description"] for tc in data]
    assert "Test case 1" in descriptions
    assert "Test case 2" in descriptions
    
    # Check response format
    for test_case in data:
        assert "id" in test_case
        assert "task_id" in test_case
        assert "description" in test_case
        assert "created_at" in test_case


@pytest.mark.asyncio
async def test_list_test_cases_empty(client: AsyncClient, test_session):
    """Test listing test cases for a task with no test cases."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    response = await client.get(f"/test-cases/tasks/{task.id}/test-cases")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_test_cases_task_not_found(client: AsyncClient):
    """Test listing test cases for non-existent task."""
    response = await client.get("/test-cases/tasks/999/test-cases")
    assert response.status_code == 404
    
    data = response.json()
    assert "Task with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_get_test_case(client: AsyncClient, test_session):
    """Test getting a specific test case by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = TestCase(
        task_id=task.id,
        description="Test case for retrieval",
        arguments={"input": "test input"},
        expected_output="expected output",
    )
    test_session.add(test_case)
    await test_session.commit()

    response = await client.get(f"/test-cases/test-cases/{test_case.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_case.id
    assert data["description"] == "Test case for retrieval"
    assert data["arguments"] == {"input": "test input"}
    assert data["expected_output"] == "expected output"
    assert data["task_id"] == task.id
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_test_case_not_found(client: AsyncClient):
    """Test getting a non-existent test case."""
    response = await client.get("/test-cases/test-cases/999")
    assert response.status_code == 404
    
    data = response.json()
    assert "Test case with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_update_test_case(client: AsyncClient, test_session):
    """Test updating a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = TestCase(
        task_id=task.id,
        description="Original description",
        arguments={"input": "original input"},
        expected_output="original expected",
    )
    test_session.add(test_case)
    await test_session.commit()

    payload = {
        "description": "Updated description",
        "expected_output": "Updated expected output"
    }

    response = await client.patch(f"/test-cases/test-cases/{test_case.id}", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["expected_output"] == "Updated expected output"
    assert data["arguments"] == {"input": "original input"}  # Should remain unchanged
    assert data["task_id"] == task.id


@pytest.mark.asyncio
async def test_update_test_case_partial(client: AsyncClient, test_session):
    """Test partial update of a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = TestCase(
        task_id=task.id,
        description="Original description",
        arguments={"input": "original input"},
        expected_output="original expected",
    )
    test_session.add(test_case)
    await test_session.commit()

    payload = {
        "description": "Updated description only"
    }

    response = await client.patch(f"/test-cases/test-cases/{test_case.id}", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["description"] == "Updated description only"
    assert data["expected_output"] == "original expected"  # Should remain unchanged
    assert data["arguments"] == {"input": "original input"}  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_test_case_not_found(client: AsyncClient):
    """Test updating a non-existent test case."""
    payload = {
        "description": "Updated description"
    }

    response = await client.patch("/test-cases/test-cases/999", json=payload)
    assert response.status_code == 404
    
    data = response.json()
    assert "Test case with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_delete_test_case(client: AsyncClient, test_session):
    """Test deleting a test case."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    test_case = TestCase(
        task_id=task.id,
        description="Test case to delete",
        arguments={"input": "test input"},
        expected_output="expected output",
    )
    test_session.add(test_case)
    await test_session.commit()

    response = await client.delete(f"/test-cases/test-cases/{test_case.id}")
    assert response.status_code == 204

    # Verify test case is deleted
    test_case_query = select(TestCase).where(TestCase.id == test_case.id)
    test_case_result = await test_session.execute(test_case_query)
    deleted_test_case = test_case_result.scalar_one_or_none()
    assert deleted_test_case is None


@pytest.mark.asyncio
async def test_delete_test_case_not_found(client: AsyncClient):
    """Test deleting a non-existent test case."""
    response = await client.delete("/test-cases/test-cases/999")
    assert response.status_code == 404
    
    data = response.json()
    assert "Test case with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_test_case_with_complex_arguments(client: AsyncClient, test_session):
    """Test creating a test case with complex arguments."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    complex_arguments = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What's 2+2?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "metadata": {
            "session_id": "abc123",
            "user_preferences": {
                "language": "en",
                "style": "formal"
            }
        }
    }

    payload = {
        "description": "Complex test case with nested arguments",
        "arguments": complex_arguments,
        "expected_output": "4"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["arguments"] == complex_arguments
    assert data["description"] == "Complex test case with nested arguments"


@pytest.mark.asyncio
async def test_test_case_with_long_description(client: AsyncClient, test_session):
    """Test creating a test case with a long description."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    long_description = "This is a very long description that tests the maximum length validation for test case descriptions. " * 10

    payload = {
        "description": long_description,
        "expected_output": "Expected result"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 422
    
    data = response.json()
    # Check that validation error occurred for description length
    assert "detail" in data


@pytest.mark.asyncio
async def test_test_case_with_empty_arguments(client: AsyncClient, test_session):
    """Test creating a test case with empty arguments."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "description": "Test case with empty arguments",
        "arguments": {},
        "expected_output": "Expected result"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["arguments"] == {}


@pytest.mark.asyncio
async def test_test_case_with_null_values(client: AsyncClient, test_session):
    """Test creating a test case with null values for optional fields."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    task = Task(project_id=project.id)
    test_session.add(task)
    await test_session.flush()

    payload = {
        "description": None,
        "arguments": None,
        "expected_output": "Expected result"
    }

    response = await client.post(f"/test-cases/tasks/{task.id}/test-cases", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["description"] is None
    assert data["arguments"] is None
    assert data["expected_output"] == "Expected result"
