"""Add invite_token and feedback tables

Revision ID: 003_add_invites_feedback
Revises: 002_add_auth_fields
Create Date: 2024-12-24

"""
from typing import Sequence, Union
from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_invites_feedback'
down_revision: Union[str, None] = '002_add_auth_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add invite_token and feedback tables."""
    
    # ==========================================
    # invite_token - Secure invite links
    # ==========================================
    op.create_table(
        'invite_token',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('token', sa.String(64), unique=True, nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False),
        sa.Column('used_by_user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_invite_token_token', 'invite_token', ['token'], unique=True)
    op.create_index('ix_invite_token_agreement_id', 'invite_token', ['agreement_id'])
    op.create_index('ix_invite_token_email', 'invite_token', ['email'])
    
    # ==========================================
    # feedback - Roommate ratings and feedback
    # ==========================================
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('to_user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),  # 1-5 stars
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('categories', sa.JSON(), nullable=True),  # {"cleanliness": 4, "communication": 5}
        sa.Column('is_anonymous', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_feedback_agreement_id', 'feedback', ['agreement_id'])
    op.create_index('ix_feedback_from_user_id', 'feedback', ['from_user_id'])
    op.create_index('ix_feedback_to_user_id', 'feedback', ['to_user_id'])


def downgrade() -> None:
    """Remove invite_token and feedback tables."""
    op.drop_table('feedback')
    op.drop_table('invite_token')
