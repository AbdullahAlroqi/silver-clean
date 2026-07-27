"""add checkout sessions for abandoned carts

Revision ID: 6e0d8b3f2a51
Revises: 5d9c7a2e1f40
Create Date: 2026-07-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '6e0d8b3f2a51'
down_revision = '5d9c7a2e1f40'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'checkout_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('flow_type', sa.String(length=30), nullable=False),
        sa.Column('page_name', sa.String(length=100), nullable=False),
        sa.Column('step_name', sa.String(length=100), nullable=True),
        sa.Column('form_data', sa.Text(), nullable=True),
        sa.Column('city_id', sa.Integer(), nullable=True),
        sa.Column('neighborhood_id', sa.Integer(), nullable=True),
        sa.Column('estimated_total', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['city_id'], ['city.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['user.id']),
        sa.ForeignKeyConstraint(['neighborhood_id'], ['neighborhood.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_checkout_session_token', 'checkout_session', ['token'], unique=True)
    op.create_index('ix_checkout_session_customer_id', 'checkout_session', ['customer_id'])
    op.create_index('ix_checkout_session_flow_type', 'checkout_session', ['flow_type'])
    op.create_index('ix_checkout_session_city_id', 'checkout_session', ['city_id'])
    op.create_index('ix_checkout_session_neighborhood_id', 'checkout_session', ['neighborhood_id'])
    op.create_index('ix_checkout_session_status', 'checkout_session', ['status'])
    op.create_index('ix_checkout_session_last_activity_at', 'checkout_session', ['last_activity_at'])


def downgrade():
    op.drop_table('checkout_session')
