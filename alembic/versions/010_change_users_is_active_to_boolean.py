"""change users.is_active to boolean

Revision ID: 010_change_users_is_active_to_boolean
Revises: 009_add_patient_facility_id
Create Date: 2026-05-25 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_users_is_active_bool' 
down_revision = '009_add_patient_facility_id'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # PostgreSQL specific cast using the USING clause for both tables
        op.execute('ALTER TABLE users ALTER COLUMN is_active TYPE BOOLEAN USING is_active::boolean')
        op.execute('ALTER TABLE facilities ALTER COLUMN is_active TYPE BOOLEAN USING is_active::boolean')
        
        # Set default values to ensure new records are active by default
        op.execute('ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true')
        op.execute('ALTER TABLE facilities ALTER COLUMN is_active SET DEFAULT true')
    # SQLite is already Boolean from 001_initial, no action needed


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Revert columns to VARCHAR if necessary
        op.execute('ALTER TABLE users ALTER COLUMN is_active TYPE VARCHAR USING is_active::text')
        op.execute('ALTER TABLE facilities ALTER COLUMN is_active TYPE VARCHAR USING is_active::text')
