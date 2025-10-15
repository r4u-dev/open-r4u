"""Project model for organizing traces."""

from app.models.base import Base, created_at_col, intpk, updated_at_col
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Project(Base):
    """Project model for organizing traces."""

    __tablename__ = "project"
    __table_args__ = (Index("ix_project_name", "name", unique=True),)

    id: Mapped[intpk]
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    traces: Mapped[list["Trace"]] = relationship(  # type: ignore
        "Trace",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]
