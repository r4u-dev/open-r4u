from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project


async def get_project(project_id: int, db: AsyncSession) -> Project | None:
    """Retrieve a project by its ID."""
    return await db.scalar(select(Project).where(Project.id == project_id))


async def get_project_by_name(project_name: str, db: AsyncSession) -> Project | None:
    """Retrieve a project by its name."""
    return await db.scalar(select(Project).where(Project.name == project_name))
