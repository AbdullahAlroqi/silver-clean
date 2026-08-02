from app import db
from app.models import User
from app.admin.routes import _normalize_whatsapp_phone

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def _create_user(app, username, role):
    with app.app_context():
        user = User(username=username, role=role)
        db.session.add(user)
        db.session.commit()
        return user.id


def test_whatsapp_phone_normalization_supports_saudi_formats():
    assert _normalize_whatsapp_phone('055 123 4567') == '966551234567'
    assert _normalize_whatsapp_phone('+966 55 123 4567') == '966551234567'
    assert _normalize_whatsapp_phone('٠٥٥١٢٣٤٥٦٧') == '966551234567'
    assert _normalize_whatsapp_phone('00966-55-123-4567') == '966551234567'


def test_supervisor_can_use_operational_pages(app):
    supervisor_id = _create_user(app, 'operations-supervisor', 'supervisor')
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, supervisor_id))

    response = client.get('/admin/bookings')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'href="/notifications"' in page
    assert 'id="notification-badge"' in page
    assert 'id="enable-notifications-btn"' in page
    assert 'data-enable-notifications' in client.get('/admin/').get_data(as_text=True)
    assert client.get('/admin/customers').status_code == 200
    assert client.get('/admin/products').status_code == 200
    assert client.get('/admin/management-reports').status_code == 200


def test_supervisor_cannot_open_admin_configuration_urls(app):
    supervisor_id = _create_user(app, 'restricted-supervisor', 'supervisor')
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, supervisor_id))

    protected_urls = [
        '/admin/services', '/admin/vehicle-sizes', '/admin/packages',
        '/admin/seasons', '/admin/locations', '/admin/settings',
        '/admin/admins', '/admin/backup/export-json', '/admin/products/add',
    ]
    for url in protected_urls:
        assert client.get(url).status_code == 403, url


def test_supervisor_cannot_delete(app):
    supervisor_id = _create_user(app, 'delete-supervisor', 'supervisor')
    customer_id = _create_user(app, 'protected-customer', 'customer')
    client = app.test_client()

    with app.app_context():
        login(client, db.session.get(User, supervisor_id))
    assert client.post(f'/admin/customers/{customer_id}/delete').status_code == 403
    with app.app_context():
        assert db.session.get(User, customer_id) is not None


def test_admin_keeps_full_access(app):
    admin_id = _create_user(app, 'full-admin', 'admin')
    admin_client = app.test_client()
    with app.app_context():
        login(admin_client, db.session.get(User, admin_id))
    assert admin_client.get('/admin/services').status_code == 200
    response = admin_client.get('/admin/settings')
    assert response.status_code == 200
    assert 'id="enable-notifications-btn"' in response.get_data(as_text=True)
