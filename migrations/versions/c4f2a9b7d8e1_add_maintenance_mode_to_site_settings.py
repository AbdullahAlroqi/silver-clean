"""Add maintenance mode to site settings

Revision ID: c4f2a9b7d8e1
Revises: b8f4d2c9a1e7
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4f2a9b7d8e1'
down_revision = 'b8f4d2c9a1e7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('site_settings')}

    if 'maintenance_mode' not in columns:
        with op.batch_alter_table('site_settings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('maintenance_mode', sa.Boolean(), nullable=True))

    site_settings = sa.table('site_settings', sa.column('maintenance_mode', sa.Boolean()))
    op.execute(site_settings.update().where(site_settings.c.maintenance_mode.is_(None)).values(maintenance_mode=False))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('site_settings')}

    if 'maintenance_mode' in columns:
        with op.batch_alter_table('site_settings', schema=None) as batch_op:
            batch_op.drop_column('maintenance_mode')
