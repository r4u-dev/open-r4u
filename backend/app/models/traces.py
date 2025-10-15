from datetime import datetime
from typing import Any

from app.enums import MessageRole
from app.models.base import Base, created_at_col, intpk, updated_at_col
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use JSONB for PostgreSQL, JSON for other databases
JSONType = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class Trace(Base):
	"""Trace model capturing LLM execution metadata and message history."""

	__tablename__ = "trace"
	__table_args__ = (
		Index("ix_trace_started_at", "started_at"),
		Index("ix_trace_model", "model"),
		Index("ix_trace_project_id", "project_id"),
	)

	id: Mapped[intpk]
	project_id: Mapped[int] = mapped_column(
		ForeignKey("project.id", ondelete="CASCADE"),
		nullable=False,
	)
	model: Mapped[str] = mapped_column(String(255), nullable=False)
	result: Mapped[str | None] = mapped_column(Text, nullable=True)
	error: Mapped[str | None] = mapped_column(Text, nullable=True)
	path: Mapped[str | None] = mapped_column(String(255), nullable=True)
	started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

	project: Mapped["Project"] = relationship("Project", back_populates="traces")  # type: ignore
	messages: Mapped[list["TraceMessage"]] = relationship(
		"TraceMessage",
		back_populates="trace",
		cascade="all, delete-orphan",
		order_by="TraceMessage.position",
	)
	tools: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)

	created_at: Mapped[created_at_col]
	updated_at: Mapped[updated_at_col]


class TraceMessage(Base):
	"""Individual message belonging to a trace."""

	__tablename__ = "trace_message"
	__table_args__ = (
		Index("ix_trace_message_trace_id_position", "trace_id", "position", unique=True),
	)

	id: Mapped[intpk]
	trace_id: Mapped[int] = mapped_column(
		ForeignKey("trace.id", ondelete="CASCADE"),
		nullable=False,
	)
	role: Mapped[MessageRole] = mapped_column(
		SQLEnum(MessageRole, name="message_role"),
		nullable=False,
	)
	content: Mapped[Any | None] = mapped_column(JSONType, nullable=True)
	position: Mapped[int] = mapped_column(Integer, nullable=False)
	name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	tool_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
	tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)

	trace: Mapped[Trace] = relationship("Trace", back_populates="messages")

	created_at: Mapped[created_at_col]
	updated_at: Mapped[updated_at_col]


