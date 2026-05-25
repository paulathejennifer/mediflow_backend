"""add notification system (placeholder)

Revision ID: add_notification_system
Revises: 005_add_updated_at_columns
Create Date: 2026-05-25 00:00:00.000000

This is a placeholder/no-op migration created to match the remote
database's alembic_version. It should be replaced with the original
migration if available.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_notification_system'
down_revision = '005_add_updated_at_columns'
branch_labels = None
depends_on = None


def upgrade():
    # No-op placeholder migration.
    pass


def downgrade():
    # No-op
    pass
