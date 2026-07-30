"""assign recovery discount codes to their customers

Revision ID: b7e31f8c2d44
Revises: 9c4d2e7a1b30
Create Date: 2026-07-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e31f8c2d44'
down_revision = '9c4d2e7a1b30'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.add_column(sa.Column('assigned_customer_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_discount_code_assigned_customer',
            'user',
            ['assigned_customer_id'],
            ['id']
        )
        batch_op.create_index(
            'ix_discount_code_assigned_customer_id',
            ['assigned_customer_id']
        )

    # Backfill every existing recovery code from the cart it was issued for.
    op.execute(sa.text(
        'UPDATE discount_code '
        'SET assigned_customer_id = ('
        'SELECT checkout_session.customer_id FROM checkout_session '
        'WHERE checkout_session.recovery_discount_code_id = discount_code.id '
        'LIMIT 1'
        ') '
        "WHERE code LIKE 'BACK%'"
    ))


def downgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.drop_index('ix_discount_code_assigned_customer_id')
        batch_op.drop_constraint(
            'fk_discount_code_assigned_customer', type_='foreignkey'
        )
        batch_op.drop_column('assigned_customer_id')
