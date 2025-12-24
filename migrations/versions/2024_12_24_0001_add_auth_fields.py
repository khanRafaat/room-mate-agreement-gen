"""Add password_hash and name columns to app_user

Revision ID: 002_add_auth_fields
Revises: 001_initial
Create Date: 2024-12-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_auth_fields'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password_hash and name columns for local authentication."""
    
    # Add password_hash column
    op.add_column(
        'app_user',
        sa.Column('password_hash', sa.String(255), nullable=True)
    )
    
    # Add name column
    op.add_column(
        'app_user',
        sa.Column('name', sa.String(255), nullable=True)
    )
    
    # Add unique index on email
    op.create_index('ix_app_user_email', 'app_user', ['email'], unique=True)


def downgrade() -> None:
    """Remove password_hash and name columns."""
    op.drop_index('ix_app_user_email', table_name='app_user')
    op.drop_column('app_user', 'name')
    op.drop_column('app_user', 'password_hash')
