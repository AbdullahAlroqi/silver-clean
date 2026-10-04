"""The Android background service talks to these endpoints, so they are
covered the same way the rest of the app is: via the real routes with a real
session cookie."""

from datetime import date, time

import pytest

from app import db
from app.models import Booking, EmployeeLocation, Notification, Service, User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


@pytest.fixture()
def people(app):
    with app.app_context():
        employee = User(username='emp', role='employee')
        customer = User(username='cust', role='customer')
        db.session.add_all([employee, customer])
        db.session.commit()
        return {'employee': employee.id, 'customer': customer.id}


def client_for(app, user_id):
    # Flask-Login caches the resolved user on the long-lived app context the
    # fixture holds, so clear it or a later client keeps the earlier identity.
    from flask import g
    g.pop('_login_user', None)
    client = app.test_client()
    login(client, db.session.get(User, user_id))
    return client


def anon_client(app):
    from flask import g
    g.pop('_login_user', None)
    return app.test_client()


def test_session_reports_role_so_only_employees_are_tracked(people, app):
    anon = anon_client(app)
    assert anon.get('/api/mobile/session').get_json() == {'authenticated': False}

    emp = client_for(app, people['employee']).get('/api/mobile/session').get_json()
    assert emp['authenticated'] is True
    assert emp['role'] == 'employee'

    cust = client_for(app, people['customer']).get('/api/mobile/session').get_json()
    assert cust['role'] == 'customer'


def test_location_is_stored_without_a_csrf_token(people, app):
    client = client_for(app, people['employee'])
    response = client.post('/api/mobile/location',
                           json={'latitude': 24.7136, 'longitude': 46.6753, 'accuracy': 12.5})
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        row = EmployeeLocation.query.filter_by(employee_id=people['employee']).first()
        assert row is not None
        assert round(row.latitude, 4) == 24.7136
        assert row.is_tracking is True


def test_repeated_heartbeat_refreshes_the_timestamp(people, app):
    client = client_for(app, people['employee'])
    payload = {'latitude': 24.7, 'longitude': 46.6, 'accuracy': 10}
    client.post('/api/mobile/location', json=payload)
    with app.app_context():
        first = EmployeeLocation.query.filter_by(employee_id=people['employee']).first().updated_at

    client.post('/api/mobile/location', json=payload)
    with app.app_context():
        second = EmployeeLocation.query.filter_by(employee_id=people['employee']).first().updated_at
    assert second >= first


def test_location_rejects_bad_input_and_non_employees(people, app):
    emp = client_for(app, people['employee'])
    assert emp.post('/api/mobile/location', json={'latitude': 'x'}).status_code == 400
    assert emp.post('/api/mobile/location', json={}).status_code == 400
    assert emp.post('/api/mobile/location',
                    json={'latitude': 999, 'longitude': 0}).status_code == 400

    cust = client_for(app, people['customer'])
    assert cust.post('/api/mobile/location',
                     json={'latitude': 24.7, 'longitude': 46.6}).status_code == 403

    anon = anon_client(app)
    assert anon.post('/api/mobile/location',
                     json={'latitude': 24.7, 'longitude': 46.6}).status_code == 401


def test_notifications_are_returned_once_per_device(people, app):
    with app.app_context():
        db.session.add_all([
            Notification(user_id=people['employee'], title='حجز جديد', message='حجز #1'),
            Notification(user_id=people['employee'], title='تنبيه', message='حجز #2'),
            Notification(user_id=people['customer'], title='ليس لك', message='خاص بالعميل'),
        ])
        db.session.commit()

    client = client_for(app, people['employee'])

    # A device that has never polled must be told where "now" is and be given
    # nothing to show, otherwise installing the app replays old history.
    first = client.get('/api/mobile/notifications?since_id=0').get_json()
    assert first['authenticated'] is True
    assert first['notifications'] == [], 'a fresh install would replay the backlog'
    seeded = first['latest_id']
    assert seeded > 0

    assert client.get('/api/mobile/notifications?since_id=%d' % seeded
                      ).get_json()['notifications'] == []

    with app.app_context():
        db.session.add(Notification(user_id=people['employee'], title='لاحق', message='حجز #3'))
        db.session.commit()
    third = client.get('/api/mobile/notifications?since_id=%d' % seeded).get_json()
    assert [n['title'] for n in third['notifications']] == ['لاحق']

    # And never twice.
    again = client.get('/api/mobile/notifications?since_id=%d' % third['latest_id']).get_json()
    assert again['notifications'] == []


def test_a_backlog_does_not_replay_page_by_page(people, app):
    """The bug that flooded the phone: walking history 20 rows per poll."""
    with app.app_context():
        for index in range(60):
            db.session.add(Notification(user_id=people['employee'],
                                        title='قديم %d' % index, message='m'))
        db.session.commit()

    client = client_for(app, people['employee'])
    body = client.get('/api/mobile/notifications?since_id=0').get_json()
    assert body['notifications'] == []
    seeded = body['latest_id']

    # Simulate a device that fell 60 behind: it must see the newest page and
    # then jump to the present, not crawl forward 20 at a time.
    behind = client.get('/api/mobile/notifications?since_id=1').get_json()
    assert len(behind['notifications']) <= 20
    assert behind['latest_id'] == seeded
    titles = [n['title'] for n in behind['notifications']]
    assert titles[-1] == 'قديم 59', 'must deliver the newest, not the oldest'
    assert titles == sorted(titles, key=lambda t: int(t.split()[1])), 'must be in order'

    # After jumping to latest_id there is nothing left to replay.
    assert client.get('/api/mobile/notifications?since_id=%d' % behind['latest_id']
                      ).get_json()['notifications'] == []


def test_notifications_do_not_touch_the_website_read_state(people, app):
    with app.app_context():
        db.session.add(Notification(user_id=people['employee'], title='ت', message='م'))
        db.session.commit()

    client = client_for(app, people['employee'])
    client.get('/api/mobile/notifications?since_id=0')
    with app.app_context():
        assert Notification.query.filter_by(user_id=people['employee']).first().read is False


def test_notifications_for_anonymous_client(people, app):
    body = anon_client(app).get('/api/mobile/notifications').get_json()
    assert body == {'authenticated': False, 'notifications': [], 'latest_id': 0}
