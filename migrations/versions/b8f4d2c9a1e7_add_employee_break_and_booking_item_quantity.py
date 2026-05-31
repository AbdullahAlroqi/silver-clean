"""Add employee break flag and booking item quantity

Revision ID: b8f4d2c9a1e7
Revises: 318556405b7e
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8f4d2c9a1e7'
down_revision = '318556405b7e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column['name'] for column in inspector.get_columns('user')}
    if 'is_on_break' not in user_columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_on_break', sa.Boolean(), nullable=True))

    if inspector.has_table('booking_item'):
        booking_item_columns = {column['name'] for column in inspector.get_columns('booking_item')}
        if 'quantity' not in booking_item_columns:
            with op.batch_alter_table('booking_item', schema=None) as batch_op:
                batch_op.add_column(sa.Column('quantity', sa.Integer(), nullable=True))
    else:
        op.create_table(
            'booking_item',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('booking_id', sa.Integer(), nullable=False),
            sa.Column('vehicle_id', sa.Integer(), nullable=False),
            sa.Column('service_id', sa.Integer(), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=True),
            sa.Column('service_price', sa.Float(), nullable=True),
            sa.Column('size_price_adjustment', sa.Float(), nullable=True),
            sa.Column('total_item_price', sa.Float(), nullable=True),
            sa.ForeignKeyConstraint(['booking_id'], ['booking.id']),
            sa.ForeignKeyConstraint(['service_id'], ['service.id']),
            sa.ForeignKeyConstraint(['vehicle_id'], ['vehicle.id']),
            sa.PrimaryKeyConstraint('id')
        )

    user_table = sa.table('user', sa.column('is_on_break', sa.Boolean()))
    booking_item_table = sa.table('booking_item', sa.column('quantity', sa.Integer()))
    op.execute(user_table.update().where(user_table.c.is_on_break.is_(None)).values(is_on_break=False))
    op.execute(booking_item_table.update().where(booking_item_table.c.quantity.is_(None)).values(quantity=1))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('booking_item'):
        booking_item_columns = {column['name'] for column in inspector.get_columns('booking_item')}
        if 'quantity' in booking_item_columns:
            with op.batch_alter_table('booking_item', schema=None) as batch_op:
                batch_op.drop_column('quantity')

    user_columns = {column['name'] for column in inspector.get_columns('user')}
    if 'is_on_break' in user_columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('is_on_break')
