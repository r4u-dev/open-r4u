"""Tests for grader API endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.enums import ScoreType
from app.models.evaluation import Grade, Grader
from app.models.projects import Project
from app.models.traces import Trace


@pytest.mark.asyncio
async def test_create_grader(client: AsyncClient, test_session):
    """Test creating a grader via API."""
    # Create project first
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    payload = {
        "name": "accuracy",
        "description": "Evaluates response accuracy",
        "prompt": "Rate the accuracy of this response: {{context}}",
        "score_type": "float",
        "model": "gpt-4",
        "temperature": 0.0,
        "max_output_tokens": 500,
        "is_active": True,
    }

    response = await client.post("/v1/graders", json={**payload, "project_id": project.id})
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "accuracy"
    assert data["description"] == "Evaluates response accuracy"
    assert data["prompt"] == "Rate the accuracy of this response: {{context}}"
    assert data["score_type"] == "float"
    assert data["model"] == "gpt-4"
    assert data["temperature"] == 0.0
    assert data["max_output_tokens"] == 500
    assert data["is_active"] is True
    assert data["project_id"] == project.id
    assert data["grade_count"] == 0
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify grader was created in database
    grader_query = select(Grader).where(Grader.id == data["id"])
    grader_result = await test_session.execute(grader_query)
    grader = grader_result.scalar_one()
    
    assert grader.name == "accuracy"
    assert grader.description == "Evaluates response accuracy"
    assert grader.score_type == ScoreType.FLOAT


@pytest.mark.asyncio
async def test_create_grader_with_reasoning_and_schema(client: AsyncClient, test_session):
    """Test creating a grader with reasoning and response schema."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    payload = {
        "name": "toxicity",
        "description": "Evaluates content toxicity",
        "prompt": "Check if this content is toxic: {{context}}",
        "score_type": "boolean",
        "model": "gpt-4",
        "temperature": 0.0,
        "reasoning": {"effort": "medium"},
        "response_schema": {
            "type": "object",
            "properties": {
                "score": {"type": "boolean"},
                "reasoning": {"type": "string"},
                "confidence": {"type": "number"}
            }
        },
        "max_output_tokens": 300,
        "is_active": True,
    }

    response = await client.post("/v1/graders", json={**payload, "project_id": project.id})
    assert response.status_code == 201
    
    data = response.json()
    assert data["score_type"] == "boolean"
    assert data["reasoning"] == {"effort": "medium"}
    assert data["response_schema"]["type"] == "object"


@pytest.mark.asyncio
async def test_create_grader_missing_required_fields(client: AsyncClient, test_session):
    """Test creating a grader with missing required fields."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    payload = {
        "name": "accuracy",
        # Missing required fields: prompt, score_type, model, max_output_tokens
    }

    response = await client.post("/v1/graders", json={**payload, "project_id": project.id})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_graders(client: AsyncClient, test_session):
    """Test listing graders for a project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    # Create graders
    grader1 = Grader(
        project_id=project.id,
        name="accuracy",
        description="Evaluates accuracy",
        prompt="Test prompt 1",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader1)

    grader2 = Grader(
        project_id=project.id,
        name="toxicity",
        description="Evaluates toxicity",
        prompt="Test prompt 2",
        score_type=ScoreType.BOOLEAN,
        model="gpt-4",
        max_output_tokens=300,
    )
    test_session.add(grader2)
    await test_session.commit()

    response = await client.get(f"/v1/graders?project_id={project.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    
    grader_names = [grader["name"] for grader in data]
    assert "accuracy" in grader_names
    assert "toxicity" in grader_names
    
    # Check that grade_count is included
    for grader in data:
        assert "grade_count" in grader
        assert grader["grade_count"] == 0


@pytest.mark.asyncio
async def test_list_graders_with_grades(client: AsyncClient, test_session):
    """Test listing graders with grade counts."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    # Create traces first
    trace1 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 1",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace1)
    
    trace2 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 2",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace2)
    await test_session.flush()

    # Create some grades
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace1.id,
        score_float=0.8,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade1)

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace2.id,
        score_float=0.9,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade2)
    await test_session.commit()

    response = await client.get(f"/v1/graders?project_id={project.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["grade_count"] == 2


@pytest.mark.asyncio
async def test_get_grader(client: AsyncClient, test_session):
    """Test getting a specific grader by ID."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        description="Evaluates accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    response = await client.get(f"/v1/graders/{grader.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == grader.id
    assert data["name"] == "accuracy"
    assert data["description"] == "Evaluates accuracy"
    assert data["prompt"] == "Test prompt"
    assert data["score_type"] == "float"
    assert data["model"] == "gpt-4"
    assert data["max_output_tokens"] == 500
    assert data["project_id"] == project.id
    assert data["grade_count"] == 0


@pytest.mark.asyncio
async def test_get_grader_not_found(client: AsyncClient):
    """Test getting a non-existent grader."""
    response = await client.get("/v1/graders/999")
    assert response.status_code == 404
    
    data = response.json()
    assert "Grader with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_get_grader_with_grades(client: AsyncClient, test_session):
    """Test getting a grader with grade count."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    # Create traces first
    trace1 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 1",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace1)
    
    trace2 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 2",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace2)
    await test_session.flush()

    # Create grades
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace1.id,
        score_float=0.8,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade1)

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace2.id,
        score_float=0.9,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade2)
    await test_session.commit()

    response = await client.get(f"/v1/graders/{grader.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["grade_count"] == 2


@pytest.mark.asyncio
async def test_update_grader(client: AsyncClient, test_session):
    """Test updating a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        description="Original description",
        prompt="Original prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        temperature=0.0,
        max_output_tokens=500,
        is_active=True,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {
        "name": "accuracy_v2",
        "description": "Updated description",
        "temperature": 0.5,
        "is_active": False,
    }

    response = await client.patch(f"/v1/graders/{grader.id}", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "accuracy_v2"
    assert data["description"] == "Updated description"
    assert data["temperature"] == 0.5
    assert data["is_active"] is False
    # These should remain unchanged
    assert data["prompt"] == "Original prompt"
    assert data["score_type"] == "float"
    assert data["model"] == "gpt-4"
    assert data["max_output_tokens"] == 500


@pytest.mark.asyncio
async def test_update_grader_partial(client: AsyncClient, test_session):
    """Test partial update of a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        description="Original description",
        prompt="Original prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        temperature=0.0,
        max_output_tokens=500,
        is_active=True,
    )
    test_session.add(grader)
    await test_session.commit()

    payload = {
        "temperature": 0.7,
    }

    response = await client.patch(f"/v1/graders/{grader.id}", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["temperature"] == 0.7
    # Everything else should remain unchanged
    assert data["name"] == "accuracy"
    assert data["description"] == "Original description"
    assert data["prompt"] == "Original prompt"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_update_grader_not_found(client: AsyncClient):
    """Test updating a non-existent grader."""
    payload = {
        "name": "updated_name",
    }

    response = await client.patch("/v1/graders/999", json=payload)
    assert response.status_code == 404
    
    data = response.json()
    assert "Grader with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_delete_grader(client: AsyncClient, test_session):
    """Test deleting a grader."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.commit()

    response = await client.delete(f"/v1/graders/{grader.id}")
    assert response.status_code == 204

    # Verify grader is deleted
    grader_query = select(Grader).where(Grader.id == grader.id)
    grader_result = await test_session.execute(grader_query)
    deleted_grader = grader_result.scalar_one_or_none()
    assert deleted_grader is None


@pytest.mark.asyncio
async def test_delete_grader_not_found(client: AsyncClient):
    """Test deleting a non-existent grader."""
    response = await client.delete("/v1/graders/999")
    assert response.status_code == 404
    
    data = response.json()
    assert "Grader with id 999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_delete_grader_with_grades(client: AsyncClient, test_session):
    """Test deleting a grader with associated grades (should cascade)."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()

    grader = Grader(
        project_id=project.id,
        name="accuracy",
        prompt="Test prompt",
        score_type=ScoreType.FLOAT,
        model="gpt-4",
        max_output_tokens=500,
    )
    test_session.add(grader)
    await test_session.flush()

    # Create traces first
    trace1 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 1",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace1)
    
    trace2 = Trace(
        project_id=project.id,
        model="gpt-4",
        result="Test response 2",
        started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(trace2)
    await test_session.flush()

    # Create grades
    grade1 = Grade(
        grader_id=grader.id,
        trace_id=trace1.id,
        score_float=0.8,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade1)

    grade2 = Grade(
        grader_id=grader.id,
        trace_id=trace2.id,
        score_float=0.9,
        grading_started_at=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        grading_completed_at=datetime(2023, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
    )
    test_session.add(grade2)
    await test_session.commit()

    response = await client.delete(f"/v1/graders/{grader.id}")
    assert response.status_code == 204

    # Verify grader and grades are deleted
    grader_query = select(Grader).where(Grader.id == grader.id)
    grader_result = await test_session.execute(grader_query)
    deleted_grader = grader_result.scalar_one_or_none()
    assert deleted_grader is None

    grade_query = select(Grade).where(Grade.grader_id == grader.id)
    grade_result = await test_session.execute(grade_query)
    deleted_grades = grade_result.scalars().all()
    assert len(deleted_grades) == 0


@pytest.mark.asyncio
async def test_list_graders_empty_project(client: AsyncClient, test_session):
    """Test listing graders for a project with no graders."""
    project = Project(name="Empty Project")
    test_session.add(project)
    await test_session.commit()

    response = await client.get(f"/v1/graders?project_id={project.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_graders_nonexistent_project(client: AsyncClient):
    """Test listing graders for a non-existent project."""
    response = await client.get("/v1/graders?project_id=999")
    assert response.status_code == 200  # Should return empty list, not error
    
    data = response.json()
    assert len(data) == 0
