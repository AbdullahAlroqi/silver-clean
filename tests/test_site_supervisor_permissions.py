import json

from app import db
from app.models import User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def _site_supervisor(app, permissions):
    with app.app_context():
        user = User(username='site-supervisor', role='site_supervisor')
        user.set_site_permissions(permissions)
        db.session.add(user)
        db.session.commit()
        return user.id


def test_site_supervisor_can_only_open_granted_sections(app):
    user_id = _site_supervisor(app, ['bookings_view', 'reports_view'])
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))

    assert client.get('/admin/').status_code == 200
    assert client.get('/admin/bookings').status_code == 200
    assert client.get('/admin/reports').status_code == 200
    assert client.get('/admin/customers').status_code == 403
    assert client.get('/admin/settings').status_code == 403


def test_site_supervisor_delete_requires_separate_permission(app):
    user_id = _site_supervisor(app, ['customers_manage'])
    with app.app_context():
        customer = User(username='protected-from-site-supervisor', role='customer')
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))
    assert client.post(f'/admin/customers/{customer_id}/delete').status_code == 403


def test_permissions_are_allowlisted_and_dashboard_is_always_available(app):
    user_id = _site_supervisor(app, ['reports_view', 'not-a-real-permission'])
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.site_permissions == {'dashboard', 'reports_view'}
        assert json.loads(user.site_permissions_json) == ['dashboard', 'reports_view']


def test_city_supervisor_remains_geographically_scoped_and_not_configurable(app):
    with app.app_context():
        city_supervisor = User(username='city-only-supervisor', role='supervisor')
        city_supervisor.set_site_permissions(['settings_manage'])
        db.session.add(city_supervisor)
        db.session.commit()
        user_id = city_supervisor.id
        assert city_supervisor.site_permissions == set()

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))
    assert client.get('/admin/settings').status_code == 403


def test_admin_can_create_site_supervisor_and_assign_permissions(app):
    with app.app_context():
        admin = User(username='permission-admin', role='admin')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    response = client.post('/admin/site-supervisors/add', data={
        'username': 'new-site-supervisor',
        'email': 'site-supervisor@example.com',
        'phone': '0500000099',
        'password': 'StrongPassword123',
        'site_permissions': ['bookings_view', 'bookings_manage', 'customers_view'],
    })
    assert response.status_code == 302
    with app.app_context():
        created = User.query.filter_by(username='new-site-supervisor').one()
        assert created.role == 'site_supervisor'
        assert created.site_permissions == {'dashboard', 'bookings_view', 'bookings_manage', 'customers_view'}
        assert not created.supervisor_cities
        assert not created.supervisor_neighborhoods


def test_site_supervisor_management_page_is_owner_admin_only(app):
    user_id = _site_supervisor(app, ['employees_manage', 'settings_manage', 'delete_records'])
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))

    assert client.get('/admin/site-supervisors').status_code == 403
    assert client.get('/admin/site-supervisors/add').status_code == 403
    employee_page = client.get('/admin/employees').get_data(as_text=True)
    assert '/admin/site-supervisors' not in employee_page


def test_read_only_permission_cannot_modify_section(app):
    user_id = _site_supervisor(app, ['customers_view'])
    with app.app_context():
        customer = User(username='read-only-customer', role='customer')
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))

    assert client.get('/admin/customers').status_code == 200
    assert client.post(f'/admin/customers/{customer_id}/reset-password').status_code == 403
    assert client.get(f'/admin/customers/{customer_id}/edit').status_code == 403
