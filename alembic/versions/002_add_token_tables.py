"""add token tables

Revision ID: 002_add_token_tables
Revises: 001_initial
Create Date: 2024-01-15 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_token_tables'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Create password_reset_tokens table
    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_password_reset_tokens_id'), 'password_reset_tokens', ['id'], unique=False)

    # Create email_verification_tokens table
    op.create_table('email_verification_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_email_verification_tokens_token'), 'email_verification_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_email_verification_tokens_id'), 'email_verification_tokens', ['id'], unique=False)


def downgrade():
    op.drop_table('email_verification_tokens')
    op.drop_table('password_reset_tokens')
