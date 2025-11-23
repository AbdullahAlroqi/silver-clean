"""add tiktok_url to site_settings

Revision ID: add_tiktok_url
Revises: f865f3df0a98
Create Date: 2025-11-21 00:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tiktok_url'
down_revision = 'f865f3df0a98'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tiktok_url', sa.String(length=200), nullable=True, server_default=''))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('tiktok_url')
