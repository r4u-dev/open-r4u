"""Change test case output to json

Revision ID: dfaa9df466bf
Revises: 9b2a3b6f3c5d
Create Date: 2025-11-04 14:33:26.122973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dfaa9df466bf'
down_revision: Union[str, Sequence[str], None] = '9b2a3b6f3c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("test_case", "expected_output")
    op.add_column(
        "test_case",
        sa.Column(
            "expected_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}"   # optional default
        )
    )
    op.alter_column(
        "test_case",
        "expected_output",
        server_default=None
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("test_case", "expected_output")

    op.add_column(
        "test_case",
        sa.Column(
            "expected_output",
            sa.Text(),
            nullable=False,
            server_default=""
        )
    )

    op.alter_column(
        "test_case",
        "expected_output",
        server_default=None
    )
