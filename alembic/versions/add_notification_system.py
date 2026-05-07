"""Add notification system tables

Revision ID: add_notification_system
Revises: previous_migration
Create Date: 2024-01-15 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_notification_system'
down_revision = 'previous_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('backend_source', sa.String(length=50), nullable=False),
        sa.Column('trigger_condition', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)

    # Create notification_delivery table
    op.create_table('notification_delivery',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('delivery_method', sa.String(length=20), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_taken', sa.String(length=100), nullable=True),
        sa.Column('action_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('delivery_status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_delivery_id'), 'notification_delivery', ['id'], unique=False)
    op.create_index(op.f('ix_notification_delivery_notification_id'), 'notification_delivery', ['notification_id'], unique=False)
    op.create_index(op.f('ix_notification_delivery_user_id'), 'notification_delivery', ['user_id'], unique=False)

    # Create system_metrics table
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('facility_id', sa.Integer(), nullable=True),
        sa.Column('service_name', sa.String(length=50), nullable=True),
        sa.Column('additional_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_metrics_id'), 'system_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_system_metrics_metric_name'), 'system_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_system_metrics_status'), 'system_metrics', ['status'], unique=False)
    op.create_index(op.f('ix_system_metrics_measured_at'), 'system_metrics', ['measured_at'], unique=False)
    op.create_index(op.f('ix_system_metrics_facility_id'), 'system_metrics', ['facility_id'], unique=False)

    # Create notification_templates table
    op.create_table('notification_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('notification_type', sa.String(length=20), nullable=False),
        sa.Column('title_template', sa.String(length=255), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('default_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('target_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('backend_source', sa.String(length=50), nullable=False),
        sa.Column('trigger_condition', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_name')
    )
    op.create_index(op.f('ix_notification_templates_id'), 'notification_templates', ['id'], unique=False)
    op.create_index(op.f('ix_notification_templates_template_name'), 'notification_templates', ['template_name'], unique=True)

    # Create notification_preferences table
    op.create_table('notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=20), nullable=False),
        sa.Column('delivery_method', sa.String(length=20), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_preferences_id'), 'notification_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

    # Create notification_queue table
    op.create_table('notification_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('delivery_method', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True, default=5),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=True, default=3),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_queue_id'), 'notification_queue', ['id'], unique=False)
    op.create_index(op.f('ix_notification_queue_notification_id'), 'notification_queue', ['notification_id'], unique=False)
    op.create_index(op.f('ix_notification_queue_target_user_id'), 'notification_queue', ['target_user_id'], unique=False)
    op.create_index(op.f('ix_notification_queue_status'), 'notification_queue', ['status'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('notification_queue')
    op.drop_table('notification_preferences')
    op.drop_table('notification_templates')
    op.drop_table('system_metrics')
    op.drop_table('notification_delivery')
    op.drop_table('notifications')
