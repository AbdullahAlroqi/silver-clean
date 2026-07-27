"""add location scope and creator to discount codes

Revision ID: 5d9c7a2e1f40
Revises: 39b15a72f6c0
Create Date: 2026-07-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '5d9c7a2e1f40'
down_revision = '39b15a72f6c0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.add_column(sa.Column('city_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('neighborhood_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_by_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_discount_code_city', 'city', ['city_id'], ['id'])
        batch_op.create_foreign_key(
            'fk_discount_code_neighborhood', 'neighborhood', ['neighborhood_id'], ['id']
        )
        batch_op.create_foreign_key('fk_discount_code_creator', 'user', ['created_by_id'], ['id'])
        batch_op.create_index('ix_discount_code_city_id', ['city_id'])
        batch_op.create_index('ix_discount_code_neighborhood_id', ['neighborhood_id'])
        batch_op.create_index('ix_discount_code_created_by_id', ['created_by_id'])


def downgrade():
    with op.batch_alter_table('discount_code') as batch_op:
        batch_op.drop_index('ix_discount_code_created_by_id')
        batch_op.drop_index('ix_discount_code_neighborhood_id')
        batch_op.drop_index('ix_discount_code_city_id')
        batch_op.drop_constraint('fk_discount_code_creator', type_='foreignkey')
        batch_op.drop_constraint('fk_discount_code_neighborhood', type_='foreignkey')
        batch_op.drop_constraint('fk_discount_code_city', type_='foreignkey')
        batch_op.drop_column('created_by_id')
        batch_op.drop_column('neighborhood_id')
        batch_op.drop_column('city_id')
