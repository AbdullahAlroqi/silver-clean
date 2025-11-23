"""merge heads

Revision ID: a83e24308ac1
Revises: 46bbfd3595a7, add_max_uses_per_customer
Create Date: 2025-11-23 13:23:01.705512

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a83e24308ac1'
down_revision = ('46bbfd3595a7', 'add_max_uses_per_customer')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
