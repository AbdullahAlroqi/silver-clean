from unittest.mock import patch

from app import db
from app.models import PushSubscription, User
from app.notifications import send_push_notification

from test_discount_location_scope import app  # noqa: F401


def test_push_delivery_waits_for_provider_acceptance(app):
    with app.app_context():
        app.config['VAPID_PRIVATE_KEY'] = 'test-private-key'
        app.config['VAPID_CLAIM_EMAIL'] = 'mailto:test@example.com'
        user = User(username='delivery-user', role='customer')
        db.session.add(user)
        db.session.flush()
        db.session.add(PushSubscription(
            user_id=user.id,
            endpoint='https://push.example/device',
            p256dh='public-key',
            auth='auth-key'
        ))
        db.session.commit()

        with patch('app.notifications.webpush') as provider:
            delivered = send_push_notification(user, {'title': 'Test', 'body': 'Test'})

        assert delivered is True
        provider.assert_called_once()
        assert provider.call_args.kwargs['timeout'] == 10
