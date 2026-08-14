"""add administrative audit log

Revision ID: d9a61e3f2b70
Revises: c8f42a6d1e90
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9a61e3f2b70'
down_revision = 'c8f42a6d1e90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_name', sa.String(length=120), nullable=False),
        sa.Column('actor_role', sa.String(length=30), nullable=True),
        sa.Column('action', sa.String(length=30), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=True),
        sa.Column('entity_id', sa.String(length=80), nullable=True),
        sa.Column('endpoint', sa.String(length=150), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('path', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('changes_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    for column in ('actor_id', 'actor_name', 'actor_role', 'action', 'entity_type',
                   'entity_id', 'endpoint', 'ip_address', 'created_at'):
        op.create_index(f'ix_audit_log_{column}', 'audit_log', [column])


def downgrade():
    op.drop_table('audit_log')
