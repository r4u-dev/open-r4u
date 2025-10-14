"""Add tool support to traces

Revision ID: 2598b50e3e46
Revises: aaa838502c9d
Create Date: 2025-10-14 18:17:35.387399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2598b50e3e46'
down_revision: Union[str, Sequence[str], None] = 'aaa838502c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "trace",
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column(
        "trace_message",
        sa.Column("name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "trace_message",
        sa.Column("tool_call_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "trace_message",
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.alter_column(
        "trace_message",
        "content",
        existing_type=sa.Text(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="to_jsonb(content)",
        existing_nullable=False,
        nullable=True,
    )

    op.execute("ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'TOOL'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE trace_message SET content = '' WHERE content IS NULL")

    op.alter_column(
        "trace_message",
        "content",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.Text(),
        postgresql_using="content::text",
        existing_nullable=True,
        nullable=False,
    )

    op.drop_column("trace_message", "tool_calls")
    op.drop_column("trace_message", "tool_call_id")
    op.drop_column("trace_message", "name")

    op.drop_column("trace", "tools")

    op.execute(
        """
        CREATE TYPE message_role_old AS ENUM ('USER', 'ASSISTANT', 'SYSTEM')
    """
    )
    op.execute(
        """
        ALTER TABLE trace_message
        ALTER COLUMN role
        TYPE message_role_old
        USING role::text::message_role_old
    """
    )
    op.execute("DROP TYPE message_role")
    op.execute("ALTER TYPE message_role_old RENAME TO message_role")
