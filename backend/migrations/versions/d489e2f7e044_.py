"""empty message

Revision ID: d489e2f7e044
Revises: 000cc9671af9, cb5cec1b033d
Create Date: 2025-10-23 17:58:53.442942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd489e2f7e044'
down_revision: Union[str, Sequence[str], None] = ('000cc9671af9', 'cb5cec1b033d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
