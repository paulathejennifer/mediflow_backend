"""add patient facility_id

Revision ID: 009_add_patient_facility_id
Revises: 008_add_updated_at_to_patient_identifiers
Create Date: 2026-05-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_add_patient_facility_id'
down_revision = '008_patient_id_updated_at'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Safe Column Addition
    columns = [c['name'] for c in inspector.get_columns('patients')]
    if 'facility_id' not in columns:
        op.add_column('patients', sa.Column('facility_id', sa.Integer(), nullable=True))
    else:
        print("Column 'facility_id' already exists in 'patients'. Skipping.")

    # 2. Safe Index Creation (No naked try/except blocks to prevent transaction poisoning)
    indexes = [idx['name'] for idx in inspector.get_indexes('patients')]
    if 'ix_patients_facility_id' not in indexes:
        op.create_index(op.f('ix_patients_facility_id'), 'patients', ['facility_id'], unique=False)
    else:
        print("Index 'ix_patients_facility_id' already exists on 'patients'. Skipping.")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Safe Index Dropping
    indexes = [idx['name'] for idx in inspector.get_indexes('patients')]
    if 'ix_patients_facility_id' in indexes:
        op.drop_index(op.f('ix_patients_facility_id'), table_name='patients')
        
    # Safe Column Dropping
    columns = [c['name'] for c in inspector.get_columns('patients')]
    if 'facility_id' in columns:
        op.drop_column('patients', 'facility_id')