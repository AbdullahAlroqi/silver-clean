"""Add service loyalty award flag

Revision ID: d6a1f4c3b9e2
Revises: c4f2a9b7d8e1
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6a1f4c3b9e2'
down_revision = 'c4f2a9b7d8e1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('service')}

    if 'awards_loyalty_point' not in columns:
        with op.batch_alter_table('service', schema=None) as batch_op:
            batch_op.add_column(sa.Column('awards_loyalty_point', sa.Boolean(), nullable=True))

    service = sa.table('service', sa.column('awards_loyalty_point', sa.Boolean()))
    op.execute(service.update().where(service.c.awards_loyalty_point.is_(None)).values(awards_loyalty_point=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('service')}

    if 'awards_loyalty_point' in columns:
        with op.batch_alter_table('service', schema=None) as batch_op:
            batch_op.drop_column('awards_loyalty_point')
