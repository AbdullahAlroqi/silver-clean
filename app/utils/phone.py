import re


_DIGIT_TRANSLATION = str.maketrans(
    '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
    '01234567890123456789',
)


def normalize_saudi_phone(value, *, allow_empty=False):
    """Return a Saudi mobile number in the canonical 05XXXXXXXX format."""
    if value is None or not str(value).strip():
        if allow_empty:
            return None
        raise ValueError('رقم الجوال مطلوب.')

    digits = re.sub(r'\D', '', str(value).translate(_DIGIT_TRANSLATION))
    if digits.startswith('00966'):
        digits = digits[5:]
    elif digits.startswith('966'):
        digits = digits[3:]
    if len(digits) == 9 and digits.startswith('5'):
        digits = '0' + digits

    if len(digits) != 10 or not digits.startswith('05'):
        raise ValueError('يجب إدخال رقم جوال سعودي صحيح يبدأ بـ 05.')
    return digits


def normalize_phone_identifier(value):
    """Normalize phone-like login/reset input and preserve usernames/emails."""
    text = str(value or '').strip()
    try:
        return normalize_saudi_phone(text)
    except ValueError:
        return text.translate(_DIGIT_TRANSLATION)
