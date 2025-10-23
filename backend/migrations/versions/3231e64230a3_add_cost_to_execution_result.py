"""add_cost_to_execution_result

Revision ID: 3231e64230a3
Revises: cb5cec1b033d
Create Date: 2025-10-23 17:48:10.600150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3231e64230a3'
down_revision: Union[str, Sequence[str], None] = 'cb5cec1b033d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add cost column to execution_result table
    op.add_column('execution_result', sa.Column('cost', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove cost column from execution_result table
    op.drop_column('execution_result', 'cost')
