"""add_task_model_and_task_id_to_traces

Revision ID: d4e5f6a7b8c9
Revises: c166fc620924
Create Date: 2025-10-15 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c166fc620924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create task table
    op.create_table(
        'task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('tools', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('response_schema', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], name='fk_task_project_id_project', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_task')
    )
    op.create_index('ix_task_model', 'task', ['model'])
    op.create_index('ix_task_project_id', 'task', ['project_id'])

    # Add task_id to trace table
    op.add_column('trace', sa.Column('task_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_trace_task_id_task',
        'trace', 'task',
        ['task_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_trace_task_id', 'trace', ['task_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove task_id from trace table
    op.drop_index('ix_trace_task_id', table_name='trace')
    op.drop_constraint('fk_trace_task_id_task', 'trace', type_='foreignkey')
    op.drop_column('trace', 'task_id')

    # Drop task table
    op.drop_index('ix_task_project_id', table_name='task')
    op.drop_index('ix_task_model', table_name='task')
    op.drop_table('task')
