from app.models import PushSubscription, User

from test_discount_location_scope import app, login  # noqa: F401


def test_customer_layout_contains_notification_activation_button(app):
    with app.app_context():
        customer = User(username='customer', role='customer')
        app.extensions['sqlalchemy'].session.add(customer)
        app.extensions['sqlalchemy'].session.commit()
        customer_id = customer.id

    client = app.test_client()
    with app.app_context():
        login(client, app.extensions['sqlalchemy'].session.get(User, customer_id))

    response = client.get('/customer/')

    assert response.status_code == 200
    assert 'id="enable-notifications-btn"' in response.get_data(as_text=True)
    assert 'data-enable-notifications' in response.get_data(as_text=True)
    assert 'data-notification-status' in response.get_data(as_text=True)
    assert response.get_data(as_text=True).count('data-notification-card') == 1


def test_employee_home_contains_notification_activation_card(app):
    with app.app_context():
        employee = User(username='notification-employee', role='employee')
        app.extensions['sqlalchemy'].session.add(employee)
        app.extensions['sqlalchemy'].session.commit()
        employee_id = employee.id

    client = app.test_client()
    with app.app_context():
        login(client, app.extensions['sqlalchemy'].session.get(User, employee_id))

    response = client.get('/employee/')
    assert response.status_code == 200
    assert 'data-enable-notifications' in response.get_data(as_text=True)
    assert 'data-notification-status' in response.get_data(as_text=True)
    assert response.get_data(as_text=True).count('data-notification-card') == 1


def test_device_status_records_installed_app_and_permission(app):
    with app.app_context():
        customer = User(username='device-status-customer', role='customer')
        app.extensions['sqlalchemy'].session.add(customer)
        app.extensions['sqlalchemy'].session.commit()
        customer_id = customer.id

    client = app.test_client()
    with app.app_context():
        login(client, app.extensions['sqlalchemy'].session.get(User, customer_id))

    response = client.post('/api/notifications/device-status', json={
        'installed': True,
        'permission': 'denied',
    })
    assert response.status_code == 200
    with app.app_context():
        customer = app.extensions['sqlalchemy'].session.get(User, customer_id)
        assert customer.has_installed_app is True
        assert customer.notification_permission == 'denied'


def test_customer_success_and_profile_have_contextual_notification_ui(app):
    with app.app_context():
        customer = User(username='contextual-notification-customer', role='customer')
        app.extensions['sqlalchemy'].session.add(customer)
        app.extensions['sqlalchemy'].session.commit()
        customer_id = customer.id

    client = app.test_client()
    with app.app_context():
        login(client, app.extensions['sqlalchemy'].session.get(User, customer_id))

    success = client.get('/customer/booking/success').get_data(as_text=True)
    profile = client.get('/customer/profile').get_data(as_text=True)
    assert 'data-post-booking-install-card' in success
    assert 'data-post-booking-notification-card' in success
    assert 'data-browser-notification-settings' in profile
    assert 'data-browser-enable-notifications' in profile


def test_admin_customer_table_shows_aggregated_notification_status(app):
    with app.app_context():
        admin = User(username='notification-status-admin', role='admin')
        customer = User(
            username='notification-status-customer', role='customer',
            has_installed_app=True, notification_permission='granted'
        )
        app.extensions['sqlalchemy'].session.add_all([admin, customer])
        app.extensions['sqlalchemy'].session.flush()
        app.extensions['sqlalchemy'].session.add(PushSubscription(
            user_id=customer.id,
            endpoint='https://push.example/status',
            p256dh='key', auth='auth'
        ))
        app.extensions['sqlalchemy'].session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, app.extensions['sqlalchemy'].session.get(User, admin_id))

    page = client.get('/admin/customers').get_data(as_text=True)
    assert 'حالة الإشعارات' in page
    assert 'مفعّل' in page
