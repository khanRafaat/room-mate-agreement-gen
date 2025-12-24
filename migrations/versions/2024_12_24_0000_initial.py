"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for the Roommate Agreement Generator."""
    
    # ==========================================
    # app_user - User accounts
    # ==========================================
    op.create_table(
        'app_user',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('b2c_sub', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # ==========================================
    # id_verification - ID verification records
    # ==========================================
    op.create_table(
        'id_verification',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),  # 'idme', 'onfido', 'persona'
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('reference_id', sa.String(255), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_id_verification_user_id', 'id_verification', ['user_id'])
    
    # ==========================================
    # file_asset - Blob storage file references
    # ==========================================
    op.create_table(
        'file_asset',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('container', sa.String(100), nullable=False),
        sa.Column('blob_name', sa.String(500), nullable=False),
        sa.Column('sha256', sa.LargeBinary(), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_file_asset_owner_id', 'file_asset', ['owner_id'])
    
    # ==========================================
    # agreement - Main agreement entity
    # ==========================================
    op.create_table(
        'agreement',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('initiator_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('title', sa.String(255), default='Roommate Agreement'),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('rent_total_cents', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_agreement_initiator_id', 'agreement', ['initiator_id'])
    op.create_index('ix_agreement_status', 'agreement', ['status'])
    
    # ==========================================
    # agreement_party - Roommates/participants
    # ==========================================
    op.create_table(
        'agreement_party',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('rent_share_cents', sa.Integer(), nullable=True),
        sa.Column('utilities', sa.JSON(), nullable=True),
        sa.Column('chores', sa.JSON(), nullable=True),
        sa.Column('signed', sa.Boolean(), default=False),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_agreement_party_agreement_id', 'agreement_party', ['agreement_id'])
    op.create_index('ix_agreement_party_email', 'agreement_party', ['email'])
    
    # ==========================================
    # agreement_terms - Agreement terms
    # ==========================================
    op.create_table(
        'agreement_terms',
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('quiet_hours', sa.JSON(), nullable=True),
        sa.Column('guest_rules', sa.JSON(), nullable=True),
        sa.Column('pet_rules', sa.JSON(), nullable=True),
        sa.Column('deposit_cents', sa.Integer(), nullable=True),
        sa.Column('deposit_forfeit_reasons', sa.JSON(), nullable=True),
        sa.Column('additional_rules', sa.Text(), nullable=True),
        sa.Column('no_offensive_clause_ack', sa.Boolean(), default=False),
    )
    
    # ==========================================
    # payment - Payment records
    # ==========================================
    op.create_table(
        'payment',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('provider_ref', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_payment_agreement_id', 'payment', ['agreement_id'])
    op.create_index('ix_payment_status', 'payment', ['status'])
    
    # ==========================================
    # signature_envelope - DocuSign tracking
    # ==========================================
    op.create_table(
        'signature_envelope',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agreement_id', sa.String(36), sa.ForeignKey('agreement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('docusign_envelope_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_signature_envelope_agreement_id', 'signature_envelope', ['agreement_id'])
    
    # ==========================================
    # notification - Sent notifications log
    # ==========================================
    op.create_table(
        'notification',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('template', sa.String(100), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_notification_user_id', 'notification', ['user_id'])
    
    # ==========================================
    # audit_log - Audit trail
    # ==========================================
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_user_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target', sa.String(255), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_log_actor_user_id', 'audit_log', ['actor_user_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('audit_log')
    op.drop_table('notification')
    op.drop_table('signature_envelope')
    op.drop_table('payment')
    op.drop_table('agreement_terms')
    op.drop_table('agreement_party')
    op.drop_table('agreement')
    op.drop_table('file_asset')
    op.drop_table('id_verification')
    op.drop_table('app_user')
