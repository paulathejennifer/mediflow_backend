"""add updated_at to patient_identifiers

Revision ID: 008_add_updated_at_to_patient_identifiers
Revises: 007_add_facility_counters
Create Date: 2026-05-20 03:07:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_updated_at_to_patient_identifiers'
down_revision = '007_add_facility_counters'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode for SQLite
    with op.batch_alter_table('patient_identifiers', recreate='auto') as batch_op:
        # Add updated_at column if missing
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Use batch mode for SQLite
    with op.batch_alter_table('patient_identifiers', recreate='auto') as batch_op:
        batch_op.drop_column('updated_at')
