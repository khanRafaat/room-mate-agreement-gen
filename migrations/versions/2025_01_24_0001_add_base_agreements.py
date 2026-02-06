"""Add base agreements with country/state/city hierarchy

Revision ID: 004_base_agreements
Revises: 003_add_invites_feedback
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_base_agreements'
down_revision: Union[str, None] = '003_add_invites_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create country, state, city, base_agreement tables and modify agreement."""
    
    # ==========================================
    # country - Countries worldwide
    # ==========================================
    op.create_table(
        'country',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(3), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # ==========================================
    # state - States/Provinces/Divisions
    # ==========================================
    op.create_table(
        'state',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('country_id', sa.String(36), sa.ForeignKey('country.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(10), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_state_country_id', 'state', ['country_id'])
    
    # ==========================================
    # city - Cities worldwide
    # ==========================================
    op.create_table(
        'city',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('state_id', sa.String(36), sa.ForeignKey('state.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_city_state_id', 'city', ['state_id'])
    
    # ==========================================
    # base_agreement - City-specific agreement templates
    # ==========================================
    op.create_table(
        'base_agreement',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('city_id', sa.String(36), sa.ForeignKey('city.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('version', sa.String(20), default='1.0.0'),
        sa.Column('content', sa.Text().with_variant(sa.Text(length=16777215), 'mysql'), nullable=True),  # MEDIUMTEXT for MySQL
        sa.Column('applicable_for', sa.String(50), default='both'),  # 'landlord', 'tenant', 'both'
        sa.Column('is_active', sa.Boolean(), default=True, server_default='1'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_base_agreement_city_id', 'base_agreement', ['city_id'])
    op.create_index('ix_base_agreement_is_active', 'base_agreement', ['is_active'])
    
    # ==========================================
    # Modify agreement table - add new columns
    # ==========================================
    op.add_column('agreement', sa.Column('base_agreement_id', sa.String(36), sa.ForeignKey('base_agreement.id'), nullable=True))
    op.add_column('agreement', sa.Column('owner_name', sa.String(255), nullable=True))
    op.add_column('agreement', sa.Column('tenant_name', sa.String(255), nullable=True))
    op.create_index('ix_agreement_base_agreement_id', 'agreement', ['base_agreement_id'])


def downgrade() -> None:
    """Drop base agreement tables and remove columns from agreement."""
    # Remove columns from agreement
    op.drop_index('ix_agreement_base_agreement_id', table_name='agreement')
    op.drop_column('agreement', 'tenant_name')
    op.drop_column('agreement', 'owner_name')
    op.drop_column('agreement', 'base_agreement_id')
    
    # Drop tables in reverse order
    op.drop_table('base_agreement')
    op.drop_table('city')
    op.drop_table('state')
    op.drop_table('country')
