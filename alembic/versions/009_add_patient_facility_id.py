"""add patient facility_id

Revision ID: 009_add_patient_facility_id
Revises: 008_add_updated_at_to_patient_identifiers
Create Date: 2026-05-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_add_patient_facility_id'
down_revision = '008_add_updated_at_to_patient_identifiers'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable facility_id to patients to reconcile prod schema drift
    op.add_column('patients', sa.Column('facility_id', sa.Integer(), nullable=True))
    try:
        op.create_index(op.f('ix_patients_facility_id'), 'patients', ['facility_id'], unique=False)
    except Exception:
        # index may already exist
        pass


def downgrade():
    try:
        op.drop_index(op.f('ix_patients_facility_id'), table_name='patients')
    except Exception:
        pass
    op.drop_column('patients', 'facility_id')
