"""Saved addresses let a customer rebook from a known location instead of
re-pinning the map. The coordinates are the source of truth: the stored
city/neighborhood is display-only, and saving is refused outside the service area.
"""
import json
from datetime import datetime, timedelta

from flask import g

from app import db
from app.models import City, Neighborhood, SavedAddress, User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


# A square around (24.70, 46.70) and a second one far from it.
SERVED_BOUNDARY = {
    'type': 'Polygon',
    'coordinates': [[[46.69, 24.69], [46.71, 24.69], [46.71, 24.71], [46.69, 24.71], [46.69, 24.69]]],
}
INSIDE = (24.70, 46.70)
OUTSIDE = (25.50, 47.50)


def build_area():
    city = City(name_ar='الرياض', name_en='Riyadh', is_active=True)
    db.session.add(city)
    db.session.flush()
    neighborhood = Neighborhood(
        city_id=city.id,
        name_ar='النرجس',
        name_en='Narjis',
        is_active=True,
        boundary_coords=json.dumps(SERVED_BOUNDARY),
    )
    customer = User(username='address-customer', role='customer')
    db.session.add_all([neighborhood, customer])
    db.session.commit()
    return {'city_id': city.id, 'neighborhood_id': neighborhood.id, 'customer_id': customer.id}


def logged_in_client(app, customer_id):
    """A client authenticated as one customer.

    The fixture holds a single app context open for the whole test and Flask-Login
    caches the loaded user on `g`, so switching identity within one test needs that
    cache dropped. In production every request gets its own context.
    """
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))
    g.pop('_login_user', None)
    return client


def save(client, label, lat, lng):
    return client.post(
        '/customer/api/saved-addresses',
        json={'label': label, 'latitude': lat, 'longitude': lng},
    )


def test_saving_a_location_fills_in_its_city_and_neighborhood(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    response = save(client, 'المنزل', *INSIDE)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['saved'] is True
    assert payload['address']['label'] == 'المنزل'
    # The customer never types the area; it is resolved from the pin.
    assert payload['address']['area_label'] == 'النرجس، الرياض'

    with app.app_context():
        stored = SavedAddress.query.one()
        assert stored.city_id == area['city_id']
        assert stored.neighborhood_id == area['neighborhood_id']
        assert stored.user_id == area['customer_id']


def test_a_location_outside_the_service_area_is_refused(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    response = save(client, 'الشاليه', *OUTSIDE)

    assert response.status_code == 400
    assert response.get_json()['saved'] is False
    with app.app_context():
        assert SavedAddress.query.count() == 0


def test_reusing_a_name_moves_the_pin_instead_of_duplicating(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    save(client, 'المنزل', *INSIDE)
    response = save(client, 'المنزل', 24.705, 46.705)

    assert response.get_json()['saved'] is True
    with app.app_context():
        stored = SavedAddress.query.one()  # still exactly one
        assert stored.latitude == 24.705
        assert stored.longitude == 46.705


def test_an_empty_name_is_refused(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    response = save(client, '   ', *INSIDE)

    assert response.status_code == 400
    with app.app_context():
        assert SavedAddress.query.count() == 0


def test_the_per_customer_cap_is_enforced(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    for index in range(SavedAddress.MAX_PER_CUSTOMER):
        assert save(client, 'موقع %d' % index, *INSIDE).get_json()['saved'] is True

    response = save(client, 'موقع إضافي', *INSIDE)
    assert response.status_code == 400
    with app.app_context():
        assert SavedAddress.query.count() == SavedAddress.MAX_PER_CUSTOMER


def test_most_recently_used_address_is_listed_first(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    save(client, 'المنزل', *INSIDE)
    save(client, 'العمل', 24.701, 46.701)

    with app.app_context():
        home = SavedAddress.query.filter_by(label='المنزل').one()
        home.last_used_at = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()

    labels = [item['label'] for item in client.get('/customer/api/saved-addresses').get_json()]
    assert labels[0] == 'المنزل'


def test_a_customer_cannot_see_or_delete_another_customers_address(app):
    with app.app_context():
        area = build_area()
        intruder = User(username='intruder', role='customer')
        db.session.add(intruder)
        db.session.commit()
        intruder_id = intruder.id

    owner_client = logged_in_client(app, area['customer_id'])
    address_id = save(owner_client, 'المنزل', *INSIDE).get_json()['address']['id']

    intruder_client = logged_in_client(app, intruder_id)
    assert intruder_client.get('/customer/api/saved-addresses').get_json() == []

    response = intruder_client.post('/customer/api/saved-addresses/%d/delete' % address_id)
    assert response.status_code == 404
    with app.app_context():
        assert SavedAddress.query.count() == 1, 'the address must survive the intruder'


def test_deleting_returns_the_remaining_addresses(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    home_id = save(client, 'المنزل', *INSIDE).get_json()['address']['id']
    save(client, 'العمل', 24.701, 46.701)

    response = client.post('/customer/api/saved-addresses/%d/delete' % home_id)

    assert response.get_json()['deleted'] is True
    assert [item['label'] for item in response.get_json()['addresses']] == ['العمل']


def test_the_booking_form_renders_the_saved_address_picker(app):
    with app.app_context():
        area = build_area()

    client = logged_in_client(app, area['customer_id'])
    page = client.get('/customer/book').get_data(as_text=True)

    assert 'saved-addresses-section' in page
    assert 'id="saved_address_id"' in page
