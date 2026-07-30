"""link recovery discount codes to abandoned checkouts

Revision ID: 9c4d2e7a1b30
Revises: 6e0d8b3f2a51
Create Date: 2026-07-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '9c4d2e7a1b30'
down_revision = '6e0d8b3f2a51'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('checkout_session') as batch_op:
        batch_op.add_column(sa.Column('recovery_discount_code_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_checkout_session_recovery_discount',
            'discount_code',
            ['recovery_discount_code_id'],
            ['id']
        )
        batch_op.create_index(
            'ix_checkout_session_recovery_discount_code_id',
            ['recovery_discount_code_id']
        )


def downgrade():
    with op.batch_alter_table('checkout_session') as batch_op:
        batch_op.drop_index('ix_checkout_session_recovery_discount_code_id')
        batch_op.drop_constraint(
            'fk_checkout_session_recovery_discount', type_='foreignkey'
        )
        batch_op.drop_column('recovery_discount_code_id')
