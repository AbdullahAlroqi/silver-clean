"""add site supervisor permissions

Revision ID: e4b73c1a9f20
Revises: d9a61e3f2b70
"""
from alembic import op
import sqlalchemy as sa


revision = 'e4b73c1a9f20'
down_revision = 'd9a61e3f2b70'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('site_permissions_json', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('site_permissions_json')
