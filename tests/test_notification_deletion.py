from datetime import datetime, timedelta

import pytest

from app import db
from app.models import Notification, User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


@pytest.mark.parametrize('role', ['customer', 'employee', 'supervisor', 'admin'])
def test_every_user_role_can_delete_own_notification(app, role):
    with app.app_context():
        user = User(username=role, role=role)
        other = User(username=f'other-{role}', role='customer')
        db.session.add_all([user, other])
        db.session.flush()
        own_notification = Notification(user_id=user.id, title='لي', message='اختبار')
        other_notification = Notification(user_id=other.id, title='للآخر', message='اختبار')
        db.session.add_all([own_notification, other_notification])
        db.session.commit()
        user_id = user.id
        own_id = own_notification.id
        other_id = other_notification.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))
    response = client.post(f'/notifications/{own_id}/delete')

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Notification, own_id) is None
        assert db.session.get(Notification, other_id) is not None


def test_delete_old_notifications_only_deletes_current_users_old_items(app):
    with app.app_context():
        user = User(username='customer', role='customer')
        other = User(username='other', role='customer')
        db.session.add_all([user, other])
        db.session.flush()
        old_date = datetime.utcnow() - timedelta(days=31)
        db.session.add_all([
            Notification(user_id=user.id, title='قديم', message='قديم', created_at=old_date),
            Notification(user_id=user.id, title='حديث', message='حديث'),
            Notification(user_id=other.id, title='قديم للآخر', message='قديم', created_at=old_date),
        ])
        db.session.commit()
        user_id = user.id
        other_id = other.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))
    response = client.post('/notifications/delete-old')

    assert response.status_code == 302
    with app.app_context():
        assert Notification.query.filter_by(user_id=user_id).count() == 1
        assert Notification.query.filter_by(user_id=other_id).count() == 1
