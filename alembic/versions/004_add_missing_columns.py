"""add missing columns to tables

Revision ID: 004_add_missing_columns
Revises: 003_add_audit_logs
Create Date: 2024-01-15 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_missing_columns'
down_revision = '003_add_audit_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to referrals table
    op.add_column('referrals', sa.Column('ai_status', sa.String(length=50), nullable=True))
    op.add_column('referrals', sa.Column('notes', sa.Text(), nullable=True))
    
    # Add missing columns to referral_documents table
    op.add_column('referral_documents', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('referral_documents', sa.Column('extracted_text', sa.Text(), nullable=True))
    op.add_column('referral_documents', sa.Column('ai_processed', sa.String(length=20), nullable=True))
    op.add_column('referral_documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add missing columns to voice_notes table
    op.add_column('voice_notes', sa.Column('processed_transcript', sa.Text(), nullable=True))
    op.add_column('voice_notes', sa.Column('ai_summary', sa.Text(), nullable=True))
    op.add_column('voice_notes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove columns from voice_notes table
    op.drop_column('voice_notes', 'updated_at')
    op.drop_column('voice_notes', 'ai_summary')
    op.drop_column('voice_notes', 'processed_transcript')
    
    # Remove columns from referral_documents table
    op.drop_column('referral_documents', 'updated_at')
    op.drop_column('referral_documents', 'ai_processed')
    op.drop_column('referral_documents', 'extracted_text')
    op.drop_column('referral_documents', 'mime_type')
    
    # Remove columns from referrals table
    op.drop_column('referrals', 'notes')
    op.drop_column('referrals', 'ai_status')
