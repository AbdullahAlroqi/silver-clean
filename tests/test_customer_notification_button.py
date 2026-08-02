from app.models import User

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
