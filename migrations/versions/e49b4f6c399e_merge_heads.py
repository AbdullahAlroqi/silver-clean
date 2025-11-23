"""merge heads

Revision ID: e49b4f6c399e
Revises: add_neighborhood_booking, manual_vehicle_id
Create Date: 2025-11-21 13:52:37.639170

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e49b4f6c399e'
down_revision = ('add_neighborhood_booking', 'manual_vehicle_id')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
