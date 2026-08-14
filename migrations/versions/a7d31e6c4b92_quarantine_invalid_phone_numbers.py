"""quarantine invalid and duplicate user phone numbers

Revision ID: a7d31e6c4b92
Revises: f2c84d7b1a63
"""
from alembic import op
import sqlalchemy as sa
import re


revision = 'a7d31e6c4b92'
down_revision = 'f2c84d7b1a63'
branch_labels = None
depends_on = None


def _canonical(value):
    if not value:
        return None
    translation = str.maketrans(
        '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789',
    )
    translated = str(value).translate(translation).strip()
    allowed = re.compile(r'[\s\u00a0\u200e\u200f\u202a-\u202e\u2066-\u2069+\-().]*')
    if not allowed.fullmatch(re.sub(r'[0-9]', '', translated)):
        return None
    digits = re.sub(r'\D', '', translated)
    if digits.startswith('00966'):
        digits = digits[5:].lstrip('0')
    elif digits.startswith('966'):
        digits = digits[3:].lstrip('0')
    if len(digits) == 9 and digits.startswith('5'):
        digits = '0' + digits
    return digits if len(digits) == 10 and digits.startswith('05') else None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('phone_needs_update', sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
        batch_op.add_column(sa.Column('original_phone', sa.String(length=100), nullable=True))

    connection = op.get_bind()
    users = connection.execute(sa.text(
        'SELECT id, phone FROM user WHERE phone IS NOT NULL ORDER BY id'
    )).fetchall()
    groups = {}
    normalized_by_id = {}
    for user_id, phone in users:
        normalized = _canonical(phone)
        normalized_by_id[user_id] = normalized
        if normalized:
            groups.setdefault(normalized, []).append((user_id, phone))

    owners = set()
    for normalized, rows in groups.items():
        exact = [user_id for user_id, phone in rows if phone == normalized]
        owners.add(min(exact) if exact else min(user_id for user_id, _ in rows))

    # Release invalid and duplicate values first to avoid unique-index conflicts.
    for user_id, phone in users:
        normalized = normalized_by_id[user_id]
        if not normalized or user_id not in owners:
            connection.execute(sa.text(
                'UPDATE user SET original_phone=:original, phone=NULL, '
                'phone_needs_update=1 WHERE id=:id'
            ), {'original': phone, 'id': user_id})

    for user_id, phone in users:
        normalized = normalized_by_id[user_id]
        if normalized and user_id in owners:
            connection.execute(sa.text(
                'UPDATE user SET phone=:phone, original_phone=NULL, '
                'phone_needs_update=0 WHERE id=:id'
            ), {'phone': normalized, 'id': user_id})


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('original_phone')
        batch_op.drop_column('phone_needs_update')
