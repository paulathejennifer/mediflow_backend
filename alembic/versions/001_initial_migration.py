"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('facility_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_facility_id'), 'users', ['facility_id'], unique=False)

    # Create facilities table
    op.create_table('facilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('facility_code', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('level', sa.String(length=50), nullable=False),
        sa.Column('county', sa.String(length=100), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('facility_code')
    )
    op.create_index(op.f('ix_facilities_facility_code'), 'facilities', ['facility_code'], unique=True)

    # Create patients table
    op.create_table('patients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('chronic_conditions', sa.Text(), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=200), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
        sa.Column('medical_history', sa.Text(), nullable=True),
        sa.Column('facility_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], )
    )
    op.create_index(op.f('ix_patients_facility_id'), 'patients', ['facility_id'], unique=False)

    # Create patient_identifiers table
    op.create_table('patient_identifiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('identifier_type', sa.String(length=50), nullable=False),
        sa.Column('identifier_value', sa.String(length=100), nullable=False),
        sa.Column('facility_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], )
    )
    op.create_index(op.f('ix_patient_identifiers_facility_id'), 'patient_identifiers', ['facility_id'], unique=False)
    op.create_index(op.f('ix_patient_identifiers_patient_id'), 'patient_identifiers', ['patient_id'], unique=False)

    # Create referrals table
    op.create_table('referrals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('from_facility_id', sa.Integer(), nullable=False),
        sa.Column('to_facility_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason_for_referral', sa.Text(), nullable=False),
        sa.Column('clinical_notes', sa.Text(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['from_facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['to_facility_id'], ['facilities.id'], )
    )
    op.create_index(op.f('ix_referrals_from_facility_id'), 'referrals', ['from_facility_id'], unique=False)
    op.create_index(op.f('ix_referrals_patient_id'), 'referrals', ['patient_id'], unique=False)
    op.create_index(op.f('ix_referrals_status'), 'referrals', ['status'], unique=False)
    op.create_index(op.f('ix_referrals_to_facility_id'), 'referrals', ['to_facility_id'], unique=False)

    # Create referral_documents table
    op.create_table('referral_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['referral_id'], ['referrals.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], )
    )
    op.create_index(op.f('ix_referral_documents_referral_id'), 'referral_documents', ['referral_id'], unique=False)

    # Create voice_notes table
    op.create_table('voice_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referral_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('audio_file_name', sa.String(length=255), nullable=False),
        sa.Column('audio_path', sa.String(length=500), nullable=False),
        sa.Column('audio_file_size', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['referral_id'], ['referrals.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], )
    )
    op.create_index(op.f('ix_voice_notes_referral_id'), 'voice_notes', ['referral_id'], unique=False)


def downgrade():
    op.drop_table('voice_notes')
    op.drop_table('referral_documents')
    op.drop_table('referrals')
    op.drop_table('patient_identifiers')
    op.drop_table('patients')
    op.drop_table('facilities')
    op.drop_table('users')
