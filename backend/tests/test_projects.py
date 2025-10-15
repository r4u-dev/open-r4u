"""Tests for project API endpoints."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project


@pytest.mark.asyncio
class TestProjectEndpoints:
    """Test project CRUD operations."""

    async def test_create_project(self, client: AsyncClient):
        """Test creating a new project."""
        payload = {
            "name": "Test Project",
            "description": "A test project",
        }

        response = await client.post("/projects", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_project_without_description(self, client: AsyncClient):
        """Test creating a project without description."""
        payload = {"name": "Minimal Project"}

        response = await client.post("/projects", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Minimal Project"
        assert data["description"] is None

    async def test_create_project_duplicate_name(self, client: AsyncClient):
        """Test that duplicate project names are rejected."""
        payload = {"name": "Duplicate Project"}

        # Create first project
        response1 = await client.post("/projects", json=payload)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = await client.post("/projects", json=payload)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    async def test_list_projects(self, client: AsyncClient):
        """Test listing all projects."""
        # Create some projects
        projects = [
            {"name": "Project 1", "description": "First"},
            {"name": "Project 2", "description": "Second"},
            {"name": "Project 3"},
        ]

        for project in projects:
            await client.post("/projects", json=project)

        # List all projects
        response = await client.get("/projects")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3
        assert all("id" in p for p in data)
        assert all("name" in p for p in data)

    async def test_get_project_by_id(self, client: AsyncClient):
        """Test getting a project by ID."""
        # Create a project
        create_response = await client.post(
            "/projects",
            json={"name": "Get By ID Test", "description": "Test description"},
        )
        project_id = create_response.json()["id"]

        # Get the project
        response = await client.get(f"/projects/{project_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Get By ID Test"
        assert data["description"] == "Test description"

    async def test_get_project_by_id_not_found(self, client: AsyncClient):
        """Test getting a non-existent project by ID."""
        response = await client.get("/projects/99999")
        assert response.status_code == 404

    async def test_get_project_by_name(self, client: AsyncClient):
        """Test getting a project by name."""
        # Create a project
        await client.post(
            "/projects",
            json={"name": "Named Project", "description": "Find by name"},
        )

        # Get by name
        response = await client.get("/projects/by-name/Named Project")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Named Project"
        assert data["description"] == "Find by name"

    async def test_get_project_by_name_not_found(self, client: AsyncClient):
        """Test getting a non-existent project by name."""
        response = await client.get("/projects/by-name/NonExistent")
        assert response.status_code == 404

    async def test_list_projects_empty(self, client: AsyncClient):
        """Test listing projects when none exist."""
        response = await client.get("/projects")
        assert response.status_code == 200
        assert response.json() == []
