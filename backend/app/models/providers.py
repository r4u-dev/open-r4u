"""Provider and Model models for managing LLM providers and their models."""

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk, updated_at_col


class Provider(Base):
    """Provider model for LLM providers (OpenAI, Anthropic, etc.)."""

    __tablename__ = "provider"
    __table_args__ = (Index("ix_provider_name", "name", unique=True),)

    id: Mapped[intpk]
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    models: Mapped[list["Model"]] = relationship(
        "Model",
        back_populates="provider",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]

    repr_cols = ("name", "display_name")


class Model(Base):
    """Model represents an LLM model available from a provider."""

    __tablename__ = "model"
    __table_args__ = (
        Index("ix_model_provider_id", "provider_id"),
        UniqueConstraint("provider_id", "name", name="uq_model_provider_name"),
    )

    id: Mapped[intpk]
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("provider.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    provider: Mapped["Provider"] = relationship("Provider", back_populates="models")

    created_at: Mapped[created_at_col]
    updated_at: Mapped[updated_at_col]

    repr_cols = ("name", "display_name", "provider_id")
