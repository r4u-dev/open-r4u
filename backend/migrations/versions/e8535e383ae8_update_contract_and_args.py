"""update_contract_and_args

Revision ID: e8535e383ae8
Revises: 3231e64230a3
Create Date: 2025-10-24 14:31:15.356136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8535e383ae8'
down_revision: Union[str, Sequence[str], None] = '3231e64230a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add response_schema column to task table
    op.add_column('task', sa.Column('response_schema', sa.JSON(), nullable=True))
    
    # Migrate response_schema from implementation to task
    # First, copy response_schema from implementation to task for each task's production version
    connection = op.get_bind()
    
    # Get all tasks with their production versions
    result = connection.execute(sa.text("""
        SELECT t.id as task_id, i.response_schema 
        FROM task t 
        JOIN implementation i ON t.production_version_id = i.id 
        WHERE i.response_schema IS NOT NULL
    """))
    
    for row in result:
        task_id, response_schema = row
        connection.execute(
            sa.text("UPDATE task SET response_schema = :response_schema WHERE id = :task_id"),
            {"response_schema": response_schema, "task_id": task_id}
        )
    
    # Remove response_schema column from implementation table
    op.drop_column('implementation', 'response_schema')
    
    # Rename variables column to arguments in execution_result table
    op.alter_column('execution_result', 'variables', new_column_name='arguments')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename arguments column back to variables in execution_result table
    op.alter_column('execution_result', 'arguments', new_column_name='variables')
    
    # Add response_schema column back to implementation table
    op.add_column('implementation', sa.Column('response_schema', sa.JSON(), nullable=True))
    
    # Migrate response_schema from task back to implementation
    # Copy response_schema from task to its production version implementation
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT t.id as task_id, t.response_schema, t.production_version_id
        FROM task t 
        WHERE t.response_schema IS NOT NULL AND t.production_version_id IS NOT NULL
    """))
    
    for row in result:
        task_id, response_schema, production_version_id = row
        connection.execute(
            sa.text("UPDATE implementation SET response_schema = :response_schema WHERE id = :implementation_id"),
            {"response_schema": response_schema, "implementation_id": production_version_id}
        )
    
    # Remove response_schema column from task table
    op.drop_column('task', 'response_schema')
