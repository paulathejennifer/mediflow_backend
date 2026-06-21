"""add updated_at columns

Revision ID: 005_add_updated_at_columns
Revises: 004_add_missing_columns
Create Date: 2024-01-15 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = '005_add_updated_at_columns'
down_revision = '004_add_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Retrieve the database connection from the active operational context
    bind = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(bind)
    
    # 1. Safe addition for 'referral_documents' table
    try:
        ref_doc_columns = [c['name'] for c in inspect_obj.get_columns('referral_documents')]
        if 'updated_at' not in ref_doc_columns:
            op.add_column('referral_documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        else:
            print("Column 'updated_at' already exists in 'referral_documents'. Skipping.")
    except Exception as e:
        # Catch fallback if the table doesn't exist yet or is locked
        print(f"Skipping updated_at addition for referral_documents: {e}")

    # 2. Safe addition for 'voice_notes' table
    try:
        voice_note_columns = [c['name'] for c in inspect_obj.get_columns('voice_notes')]
        if 'updated_at' not in voice_note_columns:
            op.add_column('voice_notes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        else:
            print("Column 'updated_at' already exists in 'voice_notes'. Skipping.")
    except Exception as e:
        print(f"Skipping updated_at addition for voice_notes: {e}")


def downgrade():
    bind = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(bind)
    
    # Safe fallback for voice_notes downgrade
    try:
        voice_note_columns = [c['name'] for c in inspect_obj.get_columns('voice_notes')]
        if 'updated_at' in voice_note_columns:
            op.drop_column('voice_notes', 'updated_at')
    except Exception as e:
        print(f"Skipping column removal for voice_notes during downgrade: {e}")

    # Safe fallback for referral_documents downgrade
    try:
        ref_doc_columns = [c['name'] for c in inspect_obj.get_columns('referral_documents')]
        if 'updated_at' in ref_doc_columns:
            op.drop_column('referral_documents', 'updated_at')
    except Exception as e:
        print(f"Skipping column removal for referral_documents during downgrade: {e}")