"""Add PDF file support to base agreements

Revision ID: 005_base_agreement_pdf
Revises: 004_base_agreements
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_base_agreement_pdf'
down_revision: Union[str, None] = '004_base_agreements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PDF file columns to base_agreement table."""
    
    # Add columns for PDF storage
    op.add_column('base_agreement', sa.Column('pdf_container', sa.String(100), nullable=True))
    op.add_column('base_agreement', sa.Column('pdf_blob_name', sa.String(500), nullable=True))
    op.add_column('base_agreement', sa.Column('pdf_filename', sa.String(255), nullable=True))
    op.add_column('base_agreement', sa.Column('pdf_size_bytes', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Remove PDF file columns from base_agreement table."""
    op.drop_column('base_agreement', 'pdf_size_bytes')
    op.drop_column('base_agreement', 'pdf_filename')
    op.drop_column('base_agreement', 'pdf_blob_name')
    op.drop_column('base_agreement', 'pdf_container')
