from datetime import datetime

from app.enums import MessageRole
from app.models.base import Base, created_at_col, intpk, updated_at_col
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Trace(Base):
	"""Trace model capturing LLM execution metadata and message history."""

	__tablename__ = "trace"
	__table_args__ = (
		Index("ix_trace_started_at", "started_at"),
		Index("ix_trace_model", "model"),
	)

	id: Mapped[intpk]
	model: Mapped[str] = mapped_column(String(255), nullable=False)
	result: Mapped[str | None] = mapped_column(Text, nullable=True)
	error: Mapped[str | None] = mapped_column(Text, nullable=True)
	started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

	messages: Mapped[list["TraceMessage"]] = relationship(
		"TraceMessage",
		back_populates="trace",
		cascade="all, delete-orphan",
		order_by="TraceMessage.position",
	)

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
	content: Mapped[str] = mapped_column(Text, nullable=False)
	position: Mapped[int] = mapped_column(Integer, nullable=False)

	trace: Mapped[Trace] = relationship("Trace", back_populates="messages")

	created_at: Mapped[created_at_col]
	updated_at: Mapped[updated_at_col]


