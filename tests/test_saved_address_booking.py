"""Booking from a saved address marks it as used, which is what keeps the most
habitual location at the front of the picker.
"""
import json
from datetime import time, timedelta

from flask import g

from app import db
from app.models import (
    Booking,
    City,
    CityServicePrice,
    EmployeeSchedule,
    Neighborhood,
    SavedAddress,
    Service,
    SiteSettings,
    User,
    Vehicle,
    VehicleSize,
)
from app.utils.timezone import get_saudi_date

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


BOUNDARY = {
    'type': 'Polygon',
    'coordinates': [[[46.69, 24.69], [46.71, 24.69], [46.71, 24.71], [46.69, 24.71], [46.69, 24.69]]],
}
INSIDE_LAT, INSIDE_LNG = 24.70, 46.70


def build_bookable_world():
    """A city/neighborhood with one employee on shift every day and one priced service."""
    tomorrow = get_saudi_date() + timedelta(days=1)

    city = City(name_ar='الرياض', name_en='Riyadh', is_active=True)
    db.session.add(city)
    db.session.flush()

    neighborhood = Neighborhood(
        city_id=city.id, name_ar='النرجس', name_en='Narjis',
        is_active=True, boundary_coords=json.dumps(BOUNDARY),
    )
    size = VehicleSize(name_ar='صغيرة', name_en='Small', price_adjustment=0, is_active=True)
    service = Service(name_ar='غسيل خارجي', name_en='Exterior', price=50, duration=60, is_active=True)
    customer = User(username='booking-customer', role='customer')
    employee = User(username='booking-employee', role='employee')
    db.session.add_all([neighborhood, size, service, customer, employee])
    db.session.flush()

    employee.neighborhoods.append(neighborhood)
    db.session.add_all([
        Vehicle(user_id=customer.id, vehicle_size_id=size.id, brand='Camry', plate_number='AAA111'),
        # The services API only offers what has a city+size price, so the booking
        # needs one too.
        CityServicePrice(city_id=city.id, service_id=service.id, vehicle_size_id=size.id,
                         price=60, is_active=True),
        EmployeeSchedule(employee_id=employee.id, day_of_week=tomorrow.weekday(),
                         start_time=time(8, 0), end_time=time(22, 0), is_active=True),
    ])

    settings = SiteSettings.get_settings()
    settings.booking_days_limit = 7
    db.session.commit()

    vehicle = Vehicle.query.filter_by(user_id=customer.id).one()
    return {
        'date': tomorrow,
        'city_id': city.id,
        'neighborhood_id': neighborhood.id,
        'customer_id': customer.id,
        'service_id': service.id,
        'vehicle_id': vehicle.id,
    }


def logged_in_client(app, customer_id):
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))
    g.pop('_login_user', None)
    return client


def booking_payload(world, **overrides):
    payload = {
        'city_id': str(world['city_id']),
        'neighborhood_id': str(world['neighborhood_id']),
        'detected_neighborhood_id': str(world['neighborhood_id']),
        'location_lat': str(INSIDE_LAT),
        'location_lng': str(INSIDE_LNG),
        'date': world['date'].isoformat(),
        'time': '10:00',
        'vehicle_ids[]': str(world['vehicle_id']),
        'service_ids[]': str(world['service_id']),
        'payment_method': 'cash',
        'submit': 'حجز',
    }
    payload.update(overrides)
    return payload


def test_booking_from_a_saved_address_marks_it_as_used(app):
    with app.app_context():
        world = build_bookable_world()

    client = logged_in_client(app, world['customer_id'])
    address_id = client.post('/customer/api/saved-addresses', json={
        'label': 'المنزل', 'latitude': INSIDE_LAT, 'longitude': INSIDE_LNG,
    }).get_json()['address']['id']

    with app.app_context():
        assert db.session.get(SavedAddress, address_id).last_used_at is None

    response = client.post(
        '/customer/book',
        data=booking_payload(world, **{'saved_address_id': str(address_id)}),
    )

    assert response.status_code == 302, 'a successful booking redirects'
    with app.app_context():
        assert Booking.query.count() == 1, 'the booking itself must be created'
        assert db.session.get(SavedAddress, address_id).last_used_at is not None


def test_booking_without_a_saved_address_touches_nothing(app):
    with app.app_context():
        world = build_bookable_world()

    client = logged_in_client(app, world['customer_id'])
    address_id = client.post('/customer/api/saved-addresses', json={
        'label': 'المنزل', 'latitude': INSIDE_LAT, 'longitude': INSIDE_LNG,
    }).get_json()['address']['id']

    response = client.post('/customer/book', data=booking_payload(world))

    assert response.status_code == 302
    with app.app_context():
        assert Booking.query.count() == 1
        assert db.session.get(SavedAddress, address_id).last_used_at is None


def test_another_customers_address_id_is_ignored_on_submit(app):
    with app.app_context():
        world = build_bookable_world()
        intruder = User(username='address-intruder', role='customer')
        db.session.add(intruder)
        db.session.commit()
        intruder_id = intruder.id

    owner_client = logged_in_client(app, world['customer_id'])
    address_id = owner_client.post('/customer/api/saved-addresses', json={
        'label': 'المنزل', 'latitude': INSIDE_LAT, 'longitude': INSIDE_LNG,
    }).get_json()['address']['id']

    # The intruder books their own vehicle but claims the owner's address id.
    with app.app_context():
        size = VehicleSize.query.first()
        db.session.add(Vehicle(user_id=intruder_id, vehicle_size_id=size.id,
                               brand='Sunny', plate_number='BBB222'))
        db.session.commit()
        intruder_vehicle_id = Vehicle.query.filter_by(user_id=intruder_id).one().id

    intruder_client = logged_in_client(app, intruder_id)
    response = intruder_client.post('/customer/book', data=booking_payload(
        world,
        **{'vehicle_ids[]': str(intruder_vehicle_id), 'saved_address_id': str(address_id)},
    ))

    assert response.status_code == 302
    with app.app_context():
        # The foreign address must stay untouched.
        assert db.session.get(SavedAddress, address_id).last_used_at is None
