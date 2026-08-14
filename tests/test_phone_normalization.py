import pytest

from app import db
from app.models import GiftOrder, User
from app.utils.phone import normalize_phone_identifier, normalize_saudi_phone

from test_discount_location_scope import TestConfig, app  # noqa: F401


@pytest.mark.parametrize('value', [
    '0551234567', '+966551234567', '966551234567', '00966551234567',
    '551234567', '+966 55 123 4567', '٠٥٥١٢٣٤٥٦٧',
])
def test_all_supported_phone_formats_become_local_05(value):
    assert normalize_saudi_phone(value) == '0551234567'


def test_invalid_non_saudi_mobile_is_rejected():
    with pytest.raises(ValueError):
        normalize_saudi_phone('12345')


def test_user_and_gift_numbers_are_canonicalized_before_storage(app):
    with app.app_context():
        user = User(username='canonical-phone-user', role='customer', phone='+966551234567')
        gift = GiftOrder(recipient_phone='00966559876543')
        db.session.add_all([user, gift])
        db.session.commit()
        assert user.phone == '0551234567'
        assert gift.recipient_phone == '0559876543'


def test_login_accepts_local_05_for_previously_international_number(app):
    with app.app_context():
        user = User(username='phone-login-user', role='customer', phone='+966551112222')
        user.set_password('ValidPassword123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    response = client.post('/auth/login', data={
        'username': '0551112222', 'password': 'ValidPassword123'
    })
    assert response.status_code == 302
    assert '/customer/' in response.headers['Location']


def test_phone_identifier_preserves_username_and_email():
    assert normalize_phone_identifier('some-user') == 'some-user'
    assert normalize_phone_identifier('user@example.com') == 'user@example.com'
