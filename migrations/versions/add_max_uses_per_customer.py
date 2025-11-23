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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'discount_code' not in tables:
        op.create_table('discount_code',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=20), nullable=False),
            sa.Column('type', sa.String(length=20), nullable=False),
            sa.Column('value', sa.Float(), nullable=False),
            sa.Column('valid_from', sa.DateTime(), nullable=True),
            sa.Column('valid_until', sa.DateTime(), nullable=False),
            sa.Column('usage_limit', sa.Integer(), nullable=True),
            sa.Column('usage_count', sa.Integer(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=True),
            sa.Column('max_uses_per_customer', sa.Integer(), nullable=True, server_default='1'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
    else:
        # Check if column exists
        columns = [c['name'] for c in inspector.get_columns('discount_code')]
        if 'max_uses_per_customer' not in columns:
            op.add_column('discount_code', sa.Column('max_uses_per_customer', sa.Integer(), nullable=True, server_default='1'))


def downgrade():
    # Remove max_uses_per_customer column
    op.drop_column('discount_code', 'max_uses_per_customer')
