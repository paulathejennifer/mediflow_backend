"""add updated_at to patient_identifiers

Revision ID: 008_add_updated_at_to_patient_identifiers
Revises: 007_add_facility_counters
Create Date: 2026-05-20 03:07:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_patient_id_updated_at' 
down_revision = '007_add_facility_counters'
branch_labels = None
depends_on = None


def upgrade():
    # Inspect the database safely first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('patient_identifiers')]
    
    if 'updated_at' not in columns:
        with op.batch_alter_table('patient_identifiers', recreate='auto') as batch_op:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    else:
        print("Column 'updated_at' already exists in 'patient_identifiers'. Skipping.")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('patient_identifiers')]
    
    if 'updated_at' in columns:
        with op.batch_alter_table('patient_identifiers', recreate='auto') as batch_op:
            batch_op.drop_column('updated_at')