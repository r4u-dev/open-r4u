"""add_projects_and_update_traces

Revision ID: 33070573efab
Revises: 2598b50e3e46
Create Date: 2025-10-15 16:17:55.734137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33070573efab'
down_revision: Union[str, Sequence[str], None] = '2598b50e3e46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create project table
    op.create_table(
        'project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_name', 'project', ['name'], unique=True)

    # Insert default project
    op.execute(
        "INSERT INTO project (name, description) VALUES ('Default Project', 'Default project for traces')"
    )

    # Add project_id to trace table
    # First, add the column as nullable
    op.add_column('trace', sa.Column('project_id', sa.Integer(), nullable=True))
    
    # Set all existing traces to the default project
    op.execute(
        "UPDATE trace SET project_id = (SELECT id FROM project WHERE name = 'Default Project')"
    )
    
    # Now make it non-nullable
    op.alter_column('trace', 'project_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_trace_project_id',
        'trace', 'project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index
    op.create_index('ix_trace_project_id', 'trace', ['project_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index and foreign key from trace
    op.drop_index('ix_trace_project_id', table_name='trace')
    op.drop_constraint('fk_trace_project_id', 'trace', type_='foreignkey')
    
    # Remove project_id column
    op.drop_column('trace', 'project_id')
    
    # Drop project table
    op.drop_index('ix_project_name', table_name='project')
    op.drop_table('project')
