"""empty message

Revision ID: f58158b8ecde
Revises: 25b0e0bf095e, ee91575c2c42
Create Date: 2025-10-30 16:12:46.749730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f58158b8ecde'
down_revision: Union[str, Sequence[str], None] = ('25b0e0bf095e', 'ee91575c2c42')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
