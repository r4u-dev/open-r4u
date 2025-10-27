"""empty message

Revision ID: 00d6b6e483a7
Revises: 956d760ec79d, e85591d36b7d
Create Date: 2025-10-27 14:45:06.161218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00d6b6e483a7'
down_revision: Union[str, Sequence[str], None] = ('956d760ec79d', 'e85591d36b7d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
