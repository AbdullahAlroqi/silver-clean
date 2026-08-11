"""add customer notification status

Revision ID: c8f42a6d1e90
Revises: b7e31f8c2d44
Create Date: 2026-08-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c8f42a6d1e90'
down_revision = 'b7e31f8c2d44'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('has_installed_app', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('notification_permission', sa.String(length=20), nullable=False, server_default='unknown'))
        batch_op.add_column(sa.Column('notification_status_updated_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('notification_status_updated_at')
        batch_op.drop_column('notification_permission')
        batch_op.drop_column('has_installed_app')
