"""drop best fields from optimization

Revision ID: 9b2a3b6f3c5d
Revises: 53914fdc7590
Create Date: 2025-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b2a3b6f3c5d'
down_revision: Union[str, Sequence[str], None] = '53914fdc7590'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop best_implementation_id and best_score columns."""
    with op.batch_alter_table('optimization') as batch_op:
        # Drop foreign key first if present (batch_alter_table handles constraints)
        try:
            batch_op.drop_constraint(
                op.f('fk_optimization_best_implementation_id_implementation'),
                type_='foreignkey',
            )
        except Exception:
            # Constraint name may differ across backends; ignore if not found
            pass
        # Drop columns
        try:
            batch_op.drop_column('best_implementation_id')
        except Exception:
            pass
        try:
            batch_op.drop_column('best_score')
        except Exception:
            pass


def downgrade() -> None:
    """Downgrade schema: re-add best_implementation_id and best_score columns (nullable)."""
    with op.batch_alter_table('optimization') as batch_op:
        batch_op.add_column(sa.Column('best_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('best_implementation_id', sa.Integer(), nullable=True))
        # Recreate foreign key to implementation.id
        batch_op.create_foreign_key(
            op.f('fk_optimization_best_implementation_id_implementation'),
            'implementation',
            ['best_implementation_id'],
            ['id'],
            ondelete='SET NULL',
        )


