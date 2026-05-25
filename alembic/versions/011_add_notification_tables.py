"""add notification tables

Revision ID: 011_add_notification_tables
Revises: 009_add_patient_facility_id
Create Date: 2026-05-25 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_add_notification_tables'
down_revision = '009_add_patient_facility_id'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    if not conn.dialect.has_table(conn, 'notifications'):
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('notification_type', sa.String(length=255), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('details', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column('actions', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column('roles', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column('backend_source', sa.String(length=255), nullable=False, server_default=sa.text("'system'")),
            sa.Column('trigger_condition', sa.Text(), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
        op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)

    if not conn.dialect.has_table(conn, 'notification_deliveries'):
        op.create_table(
            'notification_deliveries',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('notification_id', sa.Integer(), sa.ForeignKey('notifications.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('delivery_method', sa.String(length=255), nullable=False, server_default=sa.text("'websocket'")),
            sa.Column('delivery_status', sa.String(length=255), nullable=False, server_default=sa.text("'pending'")),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('action_taken', sa.String(length=255), nullable=True),
            sa.Column('action_result', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )
        op.create_index(op.f('ix_notification_deliveries_notification_id'), 'notification_deliveries', ['notification_id'], unique=False)
        op.create_index(op.f('ix_notification_deliveries_user_id'), 'notification_deliveries', ['user_id'], unique=False)

    if not conn.dialect.has_table(conn, 'notification_templates'):
        op.create_table(
            'notification_templates',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False, unique=True),
            sa.Column('notification_type', sa.String(length=255), nullable=False),
            sa.Column('title_template', sa.String(length=255), nullable=False),
            sa.Column('message_template', sa.Text(), nullable=False),
            sa.Column('default_roles', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column('backend_source', sa.String(length=255), nullable=False, server_default=sa.text("'system'")),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )

    if not conn.dialect.has_table(conn, 'system_metrics'):
        op.create_table(
            'system_metrics',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('metric_name', sa.String(length=255), nullable=False),
            sa.Column('metric_value', sa.String(length=255), nullable=True),
            sa.Column('details', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )

    if not conn.dialect.has_table(conn, 'notification_preferences'):
        op.create_table(
            'notification_preferences',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('notification_type', sa.String(length=255), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('delivery_methods', sa.JSON(), nullable=False, server_default=sa.text("'[\"websocket\"]'::json")),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

    if not conn.dialect.has_table(conn, 'notification_queue'):
        op.create_table(
            'notification_queue',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('notification_id', sa.Integer(), sa.ForeignKey('notifications.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', sa.String(length=255), nullable=False, server_default=sa.text("'pending'")),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )
        op.create_index(op.f('ix_notification_queue_notification_id'), 'notification_queue', ['notification_id'], unique=False)
        op.create_index(op.f('ix_notification_queue_user_id'), 'notification_queue', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_notification_queue_user_id'), table_name='notification_queue')
    op.drop_index(op.f('ix_notification_queue_notification_id'), table_name='notification_queue')
    op.drop_table('notification_queue')

    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')

    op.drop_table('system_metrics')

    op.drop_table('notification_templates')

    op.drop_index(op.f('ix_notification_deliveries_user_id'), table_name='notification_deliveries')
    op.drop_index(op.f('ix_notification_deliveries_notification_id'), table_name='notification_deliveries')
    op.drop_table('notification_deliveries')

    op.drop_index(op.f('ix_notifications_notification_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
