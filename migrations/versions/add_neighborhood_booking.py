"""add neighborhood_id to booking

Revision ID: add_neighborhood_booking
Revises: e28520235d7c
Create Date: 2025-11-21 13:50:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_neighborhood_booking'
down_revision = 'e28520235d7c'
branch_labels = None
depends_on = None


def upgrade():
    # Add neighborhood_id column to booking table
    with op.batch_alter_table('booking') as batch_op:
        batch_op.add_column(sa.Column('neighborhood_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_booking_neighborhood', 'neighborhood', ['neighborhood_id'], ['id'])


def downgrade():
    # Remove neighborhood_id column from booking table
    with op.batch_alter_table('booking') as batch_op:
        batch_op.drop_constraint('fk_booking_neighborhood', type_='foreignkey')
        batch_op.drop_column('neighborhood_id')
