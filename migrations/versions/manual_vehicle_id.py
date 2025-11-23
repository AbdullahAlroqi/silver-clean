"""Add vehicle_id to Subscription model manually

Revision ID: manual_vehicle_id
Revises: add_tiktok_url
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'manual_vehicle_id'
down_revision = 'add_tiktok_url'
branch_labels = None
depends_on = None


def upgrade():
    # Add vehicle_id column
    with op.batch_alter_table('subscription', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vehicle_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('subscription', schema=None) as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('vehicle_id')
