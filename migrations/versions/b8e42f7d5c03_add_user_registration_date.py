"""add user registration date

Revision ID: b8e42f7d5c03
Revises: a7d31e6c4b92
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8e42f7d5c03'
down_revision = 'a7d31e6c4b92'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_user_created_at', ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_index('ix_user_created_at')
        batch_op.drop_column('created_at')
