"""add updated_at columns

Revision ID: 005_add_updated_at_columns
Revises: 004_add_missing_columns
Create Date: 2024-01-15 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_updated_at_columns'
down_revision = '004_add_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing updated_at columns
    op.add_column('referral_documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('voice_notes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove updated_at columns
    op.drop_column('voice_notes', 'updated_at')
    op.drop_column('referral_documents', 'updated_at')
