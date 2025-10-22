"""Project API endpoints."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.projects import Project
from app.schemas.projects import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectRead]:
    """Return all projects."""
    query = select(Project).order_by(Project.name)
    result = await session.execute(query)
    projects: Sequence[Project] = result.scalars().all()

    return [ProjectRead.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Get a specific project by ID."""
    query = select(Project).where(Project.id == project_id)
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )

    return ProjectRead.model_validate(project)


@router.get("/by-name/{project_name}", response_model=ProjectRead)
async def get_project_by_name(
    project_name: str,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Get a specific project by name."""
    query = select(Project).where(Project.name == project_name)
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_name}' not found",
        )

    return ProjectRead.model_validate(project)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Create a new project."""
    # Check if project with this name already exists
    query = select(Project).where(Project.name == payload.name)
    result = await session.execute(query)
    existing_project = result.scalar_one_or_none()

    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{payload.name}' already exists",
        )

    project = Project(
        name=payload.name,
        description=payload.description,
    )

    session.add(project)
    await session.commit()
    await session.refresh(project)

    return ProjectRead.model_validate(project)
