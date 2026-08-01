from unittest.mock import patch

from app import db
from app.models import City, Neighborhood, Notification, PushSubscription, User
from app.notifications import notify_area_supervisors

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def test_area_notification_reaches_city_and_neighborhood_supervisors_once(app):
    with app.app_context():
        city = City(name_ar='الرياض')
        neighborhood = Neighborhood(name_ar='العليا', city=city)
        city_supervisor = User(username='city-supervisor', role='supervisor')
        neighborhood_supervisor = User(username='neighborhood-supervisor', role='supervisor')
        city_supervisor.supervisor_cities.append(city)
        neighborhood_supervisor.supervisor_neighborhoods.append(neighborhood)
        db.session.add_all([city, neighborhood, city_supervisor, neighborhood_supervisor])
        db.session.commit()

        with patch('app.notifications.send_push_notification', return_value=True) as send_push:
            notified = notify_area_supervisors(
                neighborhood_id=neighborhood.id,
                event_type='booking', object_id=123, customer_name='عميل'
            )

        assert notified == 2
        assert send_push.call_count == 2
        notifications = Notification.query.order_by(Notification.user_id).all()
        assert len(notifications) == 2
        assert {item.user_id for item in notifications} == {
            city_supervisor.id, neighborhood_supervisor.id
        }
        assert all(item.title == 'حجز جديد' and item.read is False for item in notifications)


def test_supervisor_browser_subscription_is_saved(app):
    with app.app_context():
        supervisor = User(username='push-supervisor', role='supervisor')
        db.session.add(supervisor)
        db.session.commit()
        supervisor_id = supervisor.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, supervisor_id))

    response = client.post('/subscribe', json={
        'endpoint': 'https://push.example/supervisor-device',
        'keys': {'p256dh': 'public-device-key', 'auth': 'auth-secret'}
    })

    assert response.status_code == 201
    with app.app_context():
        subscription = PushSubscription.query.one()
        assert subscription.user_id == supervisor_id
