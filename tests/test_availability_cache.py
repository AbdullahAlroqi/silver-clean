from app import db
from app.models import User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def test_available_times_is_never_cached(app):
    with app.app_context():
        customer = User(username='availability-customer', role='customer')
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    # Even validation/empty responses must not preserve an old schedule.
    response = client.get('/customer/api/available-times')

    assert response.status_code == 200
    assert 'no-store' in response.headers['Cache-Control']
    assert response.headers['Pragma'] == 'no-cache'
    assert response.headers['Expires'] == '0'
