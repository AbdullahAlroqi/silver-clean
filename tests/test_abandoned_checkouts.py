from datetime import datetime, timedelta

from app import db
from app.models import CheckoutSession, City, Neighborhood, User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def test_checkout_progress_records_customer_page_and_location(app):
    with app.app_context():
        customer = User(username='customer', phone='0500000000', role='customer')
        city = City(name_ar='الرياض', name_en='Riyadh')
        db.session.add_all([customer, city])
        db.session.flush()
        neighborhood = Neighborhood(name_ar='العليا', city_id=city.id)
        db.session.add(neighborhood)
        db.session.commit()
        customer_id = customer.id
        city_id = city.id
        neighborhood_id = neighborhood.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    response = client.post('/customer/api/checkout-progress', json={
        'flow_type': 'booking',
        'page_name': 'حجز خدمة',
        'step_name': 'الخطوة 2 من 4',
        'form_data': {
            'city_id': str(city_id),
            'neighborhood_id': str(neighborhood_id),
            'vehicle_id': '7',
            'csrf_token': 'must-not-be-stored',
        },
    })

    assert response.status_code == 200
    with app.app_context():
        checkout = CheckoutSession.query.one()
        assert checkout.customer_id == customer_id
        assert checkout.city_id == city_id
        assert checkout.neighborhood_id == neighborhood_id
        assert checkout.step_name == 'الخطوة 2 من 4'
        assert 'must-not-be-stored' not in checkout.form_data


def test_abandoned_checkout_page_only_shows_inactive_active_sessions(app):
    with app.app_context():
        admin = User(username='admin', role='admin')
        customer = User(username='customer', phone='0500000000', role='customer')
        db.session.add_all([admin, customer])
        db.session.flush()
        db.session.add_all([
            CheckoutSession(
                token='old-active', customer_id=customer.id, flow_type='booking',
                page_name='حجز خدمة', step_name='المراجعة', status='active',
                last_activity_at=datetime.utcnow() - timedelta(minutes=40)
            ),
            CheckoutSession(
                token='completed', customer_id=customer.id, flow_type='booking',
                page_name='حجز خدمة', step_name='المراجعة', status='completed',
                last_activity_at=datetime.utcnow() - timedelta(minutes=40)
            ),
        ])
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))
    response = client.get('/admin/abandoned-checkouts')

    assert response.status_code == 200
    assert 'old-active' not in response.get_data(as_text=True)
    assert 'حجز خدمة' in response.get_data(as_text=True)


def test_supervisor_only_sees_abandoned_checkouts_in_assigned_region(app):
    with app.app_context():
        supervisor = User(username='supervisor', role='supervisor')
        customer = User(username='customer', role='customer')
        assigned_city = City(name_ar='الرياض')
        other_city = City(name_ar='جدة')
        db.session.add_all([supervisor, customer, assigned_city, other_city])
        db.session.flush()
        assigned_neighborhood = Neighborhood(name_ar='العليا', city_id=assigned_city.id)
        other_neighborhood = Neighborhood(name_ar='الروضة', city_id=other_city.id)
        supervisor.supervisor_cities.append(assigned_city)
        db.session.add_all([assigned_neighborhood, other_neighborhood])
        db.session.flush()
        old = datetime.utcnow() - timedelta(minutes=40)
        db.session.add_all([
            CheckoutSession(
                token='assigned-region', customer_id=customer.id, flow_type='booking',
                page_name='سلة الرياض', status='active', city_id=assigned_city.id,
                neighborhood_id=assigned_neighborhood.id, last_activity_at=old
            ),
            CheckoutSession(
                token='other-region', customer_id=customer.id, flow_type='booking',
                page_name='سلة جدة', status='active', city_id=other_city.id,
                neighborhood_id=other_neighborhood.id, last_activity_at=old
            ),
        ])
        db.session.commit()
        supervisor_id = supervisor.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, supervisor_id))
    response = client.get('/admin/abandoned-checkouts')
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'سلة الرياض' in page
    assert 'سلة جدة' not in page
