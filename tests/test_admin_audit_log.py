from app import db
from app.models import AuditLog, User
from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def _user(role, username):
    user = User(username=username, role=role, points=1)
    db.session.add(user)
    db.session.commit()
    return user.id


def test_admin_change_records_actor_endpoint_ip_and_old_new_values(app):
    with app.app_context():
        admin_id = _user('admin', 'audit-admin')
        customer_id = _user('customer', 'audit-customer')
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    response = client.post(
        f'/admin/customers/{customer_id}/add-points',
        data={'points': '4'}, headers={'X-Forwarded-For': '203.0.113.20'}
    )
    assert response.status_code == 302
    with app.app_context():
        log = AuditLog.query.filter_by(entity_type='User', entity_id=str(customer_id), action='update').one()
        assert log.actor_id == admin_id
        assert log.actor_name == 'audit-admin'
        assert log.endpoint == 'admin.add_points'
        assert log.ip_address == '203.0.113.20'
        assert log.changes['points'] == {'old': 1, 'new': 5}


def test_password_values_are_redacted(app):
    with app.app_context():
        admin_id = _user('admin', 'password-auditor')
        customer_id = _user('customer', 'password-customer')
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))
    client.post(f'/admin/customers/{customer_id}/reset-password', data={'new_password': 'NeverLogThis123'})
    with app.app_context():
        log = AuditLog.query.filter_by(entity_type='User', entity_id=str(customer_id), action='update').one()
        assert log.changes['password_hash'] == {'old': '<redacted>', 'new': '<redacted>'}
        assert 'NeverLogThis123' not in log.changes_json


def test_only_admin_can_view_and_export_audit_log(app):
    with app.app_context():
        admin_id = _user('admin', 'audit-view-admin')
        supervisor_id = _user('supervisor', 'audit-view-supervisor')
    admin_client = app.test_client()
    supervisor_client = app.test_client()
    with app.app_context():
        login(admin_client, db.session.get(User, admin_id))
        login(supervisor_client, db.session.get(User, supervisor_id))
    page = admin_client.get('/admin/audit-logs')
    assert page.status_code == 200
    assert 'سجل التدقيق الإداري' in page.get_data(as_text=True)
    assert admin_client.get('/admin/audit-logs/export').status_code == 200
    # The shared test app context keeps Flask-Login's g cache between clients;
    # production requests each receive a fresh application context.
    from flask import g
    g.pop('_login_user', None)
    assert supervisor_client.get('/admin/audit-logs').status_code == 403
    g.pop('_login_user', None)
    assert supervisor_client.get('/admin/audit-logs/export').status_code == 403
