import re


_DIGIT_TRANSLATION = str.maketrans(
    '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
    '01234567890123456789',
)

# Formatting characters accepted around/between digits. Alphabetic characters
# are deliberately excluded so values such as "0551234567abc" are rejected.
_ALLOWED_FORMATTING = re.compile(r'[\s\u00a0\u200e\u200f\u202a-\u202e\u2066-\u2069+\-().]*')


def normalize_saudi_phone(value, *, allow_empty=False):
    """Return a Saudi mobile number in the canonical 05XXXXXXXX format."""
    if value is None or not str(value).strip():
        if allow_empty:
            return None
        raise ValueError('رقم الجوال مطلوب.')

    translated = str(value).translate(_DIGIT_TRANSLATION).strip()
    non_digits = re.sub(r'[0-9]', '', translated)
    if not _ALLOWED_FORMATTING.fullmatch(non_digits):
        raise ValueError('رقم الجوال يجب أن يحتوي على أرقام فقط.')
    digits = re.sub(r'\D', '', translated)
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
