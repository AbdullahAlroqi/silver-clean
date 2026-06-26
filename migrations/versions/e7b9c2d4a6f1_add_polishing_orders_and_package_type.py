"""Add polishing orders and package type

Revision ID: e7b9c2d4a6f1
Revises: d6a1f4c3b9e2
Create Date: 2026-06-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7b9c2d4a6f1'
down_revision = 'd6a1f4c3b9e2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    package_columns = {column['name'] for column in inspector.get_columns('subscription_package')}
    if 'package_type' not in package_columns:
        with op.batch_alter_table('subscription_package', schema=None) as batch_op:
            batch_op.add_column(sa.Column('package_type', sa.String(length=20), nullable=True))

    subscription_package = sa.table(
        'subscription_package',
        sa.column('package_type', sa.String(length=20))
    )
    op.execute(
        subscription_package.update()
        .where(subscription_package.c.package_type.is_(None))
        .values(package_type='subscription')
    )

    tables = inspector.get_table_names()
    if 'polishing_order' not in tables:
        op.create_table(
            'polishing_order',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('vehicle_id', sa.Integer(), nullable=True),
            sa.Column('neighborhood_id', sa.Integer(), nullable=True),
            sa.Column('package_id', sa.Integer(), nullable=True),
            sa.Column('preferred_time', sa.String(length=20), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['customer_id'], ['user.id']),
            sa.ForeignKeyConstraint(['neighborhood_id'], ['neighborhood.id']),
            sa.ForeignKeyConstraint(['package_id'], ['subscription_package.id']),
            sa.ForeignKeyConstraint(['vehicle_id'], ['vehicle.id']),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'polishing_order' in inspector.get_table_names():
        op.drop_table('polishing_order')

    package_columns = {column['name'] for column in inspector.get_columns('subscription_package')}
    if 'package_type' in package_columns:
        with op.batch_alter_table('subscription_package', schema=None) as batch_op:
            batch_op.drop_column('package_type')
