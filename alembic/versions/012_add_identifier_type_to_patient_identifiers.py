"""add identifier_type to patient_identifiers

Revision ID: 012_add_identifier_type
Revises: 011_add_notification_tables
Create Date: 2024-05-24 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_add_identifier_type'
down_revision = '011_add_notification_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Check if the column already exists to avoid "duplicate column" errors
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('patient_identifiers')]
    
    if 'identifier_type' not in columns:
        # Add the missing identifier_type column
        op.add_column('patient_identifiers', sa.Column('identifier_type', sa.String(length=50), nullable=True))


def downgrade():
    # Remove the identifier_type column
    op.drop_column('patient_identifiers', 'identifier_type')