"""change users.is_active to boolean

Revision ID: 010_change_users_is_active_to_boolean
Revises: 009_add_patient_facility_id
Create Date: 2026-05-25 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_change_users_is_active_to_boolean'
down_revision = '009_add_patient_facility_id'
branch_labels = None
depends_on = None


def upgrade():
    # Convert textual 'true'/'false' values to boolean
    op.execute("ALTER TABLE users ALTER COLUMN is_active TYPE boolean USING (is_active::boolean);")


def downgrade():
    # Revert to varchar
    op.execute("ALTER TABLE users ALTER COLUMN is_active TYPE varchar USING (CASE WHEN is_active THEN 'true' ELSE 'false' END);")
