"""add facility counters

Revision ID: 007_add_facility_counters
Revises: 006_add_refresh_tokens
Create Date: 2026-05-20 01:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_facility_counters'
down_revision = '006_add_refresh_tokens'
branch_labels = None
depends_on = None


def upgrade():
    # Create facility_counters table
    op.create_table(
        'facility_counters',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id'), unique=True, nullable=False),
        sa.Column('last_patient_number', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create index on facility_id
    op.create_index('ix_facility_counters_facility_id', 'facility_counters', ['facility_id'])


def downgrade():
    # Drop facility_counters table
    op.drop_index('ix_facility_counters_facility_id', table_name='facility_counters')
    op.drop_table('facility_counters')
