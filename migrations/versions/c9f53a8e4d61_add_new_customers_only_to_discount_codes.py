"""add new customers only restriction to discount codes

Revision ID: c9f53a8e4d61
Revises: b8e42f7d5c03
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9f53a8e4d61'
down_revision = 'b8e42f7d5c03'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.add_column(sa.Column(
            'new_customers_only', sa.Boolean(), nullable=False,
            server_default=sa.false()
        ))


def downgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.drop_column('new_customers_only')
