"""normalize Saudi phone numbers to 05 format

Revision ID: f2c84d7b1a63
Revises: e4b73c1a9f20
"""
from alembic import op
import sqlalchemy as sa
import re


revision = 'f2c84d7b1a63'
down_revision = 'e4b73c1a9f20'
branch_labels = None
depends_on = None


def _canonical(value):
    if not value:
        return value
    translation = str.maketrans(
        '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789',
    )
    digits = re.sub(r'\D', '', str(value).translate(translation))
    had_country_prefix = False
    if digits.startswith('00966'):
        digits = digits[5:]
        had_country_prefix = True
    elif digits.startswith('966'):
        digits = digits[3:]
        had_country_prefix = True
    if had_country_prefix:
        digits = digits.lstrip('0')
    if len(digits) == 9 and digits.startswith('5'):
        digits = '0' + digits
    if had_country_prefix and digits.startswith('5'):
        return '0' + digits
    return digits if len(digits) == 10 and digits.startswith('05') else value


def upgrade():
    connection = op.get_bind()
    users = connection.execute(sa.text('SELECT id, phone FROM user WHERE phone IS NOT NULL')).fetchall()
    canonical_owners = {}
    for user_id, phone in users:
        normalized = _canonical(phone)
        if normalized in canonical_owners and canonical_owners[normalized] != user_id:
            raise RuntimeError(
                f'Duplicate phone accounts must be resolved before migration: {normalized} '
                f'(user IDs {canonical_owners[normalized]} and {user_id})'
            )
        canonical_owners[normalized] = user_id
    for user_id, phone in users:
        normalized = _canonical(phone)
        if normalized != phone:
            connection.execute(sa.text('UPDATE user SET phone=:phone WHERE id=:id'),
                               {'phone': normalized, 'id': user_id})

    gifts = connection.execute(sa.text(
        'SELECT id, recipient_phone FROM gift_order WHERE recipient_phone IS NOT NULL'
    )).fetchall()
    for gift_id, phone in gifts:
        normalized = _canonical(phone)
        if normalized != phone:
            connection.execute(sa.text(
                'UPDATE gift_order SET recipient_phone=:phone WHERE id=:id'
            ), {'phone': normalized, 'id': gift_id})


def downgrade():
    # Canonical local numbers are valid and should not be converted back.
    pass
