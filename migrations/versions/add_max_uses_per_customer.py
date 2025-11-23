"""Add max_uses_per_customer to DiscountCode

Revision ID: add_max_uses_per_customer
Revises: 
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_max_uses_per_customer'
down_revision = 'add_tiktok_url'
branch_labels = None
depends_on = None


def upgrade():
    # Add max_uses_per_customer column to discount_code table
    op.add_column('discount_code', sa.Column('max_uses_per_customer', sa.Integer(), nullable=True, server_default='1'))


def downgrade():
    # Remove max_uses_per_customer column
    op.drop_column('discount_code', 'max_uses_per_customer')
