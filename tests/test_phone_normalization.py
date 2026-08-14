from datetime import datetime

import pytest

from app import db
from app.models import GiftOrder, User
from app.utils.phone import normalize_phone_identifier, normalize_saudi_phone

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


@pytest.mark.parametrize('value', [
    '0551234567', '+966551234567', '966551234567', '00966551234567',
    '551234567', '+966 55 123 4567', '٠٥٥١٢٣٤٥٦٧',
])
def test_all_supported_phone_formats_become_local_05(value):
    assert normalize_saudi_phone(value) == '0551234567'


def test_invalid_non_saudi_mobile_is_rejected():
    with pytest.raises(ValueError):
        normalize_saudi_phone('12345')
    with pytest.raises(ValueError):
        normalize_saudi_phone('0551234567letters')


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


def test_quarantined_user_must_update_phone_before_using_site(app):
    with app.app_context():
        user = User(username='quarantined-phone-user', role='customer',
                    phone_needs_update=True, original_phone='not-a-phone')
        user.set_password('ValidPassword123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    response = client.post('/auth/login', data={
        'username': 'quarantined-phone-user', 'password': 'ValidPassword123'
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/auth/update-phone')
    assert client.get('/customer/').headers['Location'].endswith('/auth/update-phone')

    response = client.post('/auth/update-phone', data={'phone': '+966551239999'})
    assert response.status_code == 302
    with app.app_context():
        updated = User.query.filter_by(username='quarantined-phone-user').one()
        assert updated.phone == '0551239999'
        assert updated.phone_needs_update is False
        assert updated.original_phone is None


def test_invalid_phones_page_shows_registration_and_last_order_dates(app):
    with app.app_context():
        admin = User(username='invalid-phone-admin', role='admin')
        customer = User(
            username='dated-invalid-phone', role='customer',
            phone_needs_update=True, original_phone='invalid',
            created_at=datetime(2026, 1, 2, 10, 30),
        )
        db.session.add_all([admin, customer])
        db.session.flush()
        db.session.add(GiftOrder(
            sender_id=customer.id,
            created_at=datetime(2026, 7, 8, 14, 45),
        ))
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    response = client.get('/admin/invalid-phones')
    assert response.status_code == 200
    assert '2026-01-02 10:30' in response.get_data(as_text=True)
    assert '2026-07-08 14:45' in response.get_data(as_text=True)
