"""The 'nearest appointment' suggestion box walks /customer/api/available-times
day by day from the server's Saudi date and keeps the first day that has slots.
These tests exercise that walk the same way the booking form does.
"""
from datetime import time, timedelta

from app import db
from app.models import (
    Booking,
    BookingItem,
    City,
    EmployeeSchedule,
    Neighborhood,
    Service,
    SiteSettings,
    User,
    Vehicle,
    VehicleSize,
)
from app.utils.timezone import get_saudi_date

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def build_scenario(open_day_offsets, booking_days_limit=7):
    """Employee works only on the weekdays matching the given day offsets."""
    today = get_saudi_date()
    city = City(name_ar='الرياض', name_en='Riyadh')
    db.session.add(city)
    db.session.flush()
    neighborhood = Neighborhood(city_id=city.id, name_ar='النرجس', name_en='Narjis')
    size = VehicleSize(name_ar='صغيرة', name_en='Small', price_adjustment=0)
    service = Service(name_ar='غسيل خارجي', name_en='Exterior', price=50, duration=60)
    customer = User(username='nearest-customer', role='customer')
    employee = User(username='nearest-employee', role='employee')
    db.session.add_all([neighborhood, size, service, customer, employee])
    db.session.flush()

    employee.neighborhoods.append(neighborhood)
    vehicle = Vehicle(user_id=customer.id, vehicle_size_id=size.id, brand='Camry', plate_number='AAA111')
    db.session.add(vehicle)

    for offset in open_day_offsets:
        day = today + timedelta(days=offset)
        db.session.add(EmployeeSchedule(
            employee_id=employee.id,
            day_of_week=day.weekday(),
            start_time=time(8, 0),
            end_time=time(22, 0),
            is_active=True,
        ))

    settings = SiteSettings.get_settings()
    settings.booking_days_limit = booking_days_limit
    db.session.commit()

    return {
        'today': today,
        'customer_id': customer.id,
        'employee_id': employee.id,
        'neighborhood_id': neighborhood.id,
        'service_id': service.id,
        'vehicle_id': vehicle.id,
    }


def walk_days(client, data, limit=7):
    """Mirror findNearestAppointment(): scan day 0..limit, keep the first hit."""
    days = []
    for offset in range(limit + 1):
        date = data['today'] + timedelta(days=offset)
        response = client.get('/customer/api/available-times', query_string={
            'date': date.isoformat(),
            'neighborhood_id': data['neighborhood_id'],
            'service_id': data['service_id'],
            'duration': 60,
            'type': 'service',
            'vehicle_ids[]': data['vehicle_id'],
        })
        assert response.status_code == 200
        payload = response.get_json()
        times = payload if isinstance(payload, list) else payload.get('available_times', [])
        error = None if isinstance(payload, list) else payload.get('error')
        days.append({'date': date, 'times': times, 'error': error})
    return days


def logged_in_client(app, customer_id):
    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))
    return client


def test_suggestion_skips_closed_days_and_lands_on_first_open_one(app):
    with app.app_context():
        # The employee only works on the weekday that falls three days out.
        data = build_scenario(open_day_offsets=[3])

    client = logged_in_client(app, data['customer_id'])
    days = walk_days(client, data)

    nearest = next((day for day in days if day['times']), None)
    assert nearest is not None, 'the suggestion box would have found nothing'
    assert nearest['date'] == data['today'] + timedelta(days=3)
    assert nearest['times'][0] == '08:00'
    # Every earlier day must be genuinely empty, otherwise the box would
    # suggest a day the employee does not work.
    assert all(not day['times'] for day in days[:3])


def test_suggestion_can_land_on_today(app):
    with app.app_context():
        data = build_scenario(open_day_offsets=[0, 1, 2, 3, 4, 5, 6])

    client = logged_in_client(app, data['customer_id'])
    days = walk_days(client, data)

    nearest = next((day for day in days if day['times']), None)
    assert nearest is not None
    # Today still counts as long as the shift has remaining slots; the endpoint
    # filters out times that already passed in Saudi time.
    assert nearest['date'] in (data['today'], data['today'] + timedelta(days=1))


def test_last_day_of_the_window_is_still_offered(app):
    with app.app_context():
        data = build_scenario(open_day_offsets=[7], booking_days_limit=7)

    client = logged_in_client(app, data['customer_id'])
    days = walk_days(client, data, limit=7)

    nearest = next((day for day in days if day['times']), None)
    assert nearest is not None, 'day 7 must stay inside the booking window'
    assert nearest['date'] == data['today'] + timedelta(days=7)


def test_active_booking_rule_is_reported_as_an_error_not_as_emptiness(app):
    with app.app_context():
        data = build_scenario(open_day_offsets=[0, 1, 2, 3, 4, 5, 6])
        # Tomorrow, so the 4-hour expiry sweep in before_request leaves it active
        # whatever time of day the suite runs at.
        blocked_date = data['today'] + timedelta(days=1)
        booking = Booking(
            customer_id=data['customer_id'],
            employee_id=data['employee_id'],
            vehicle_id=data['vehicle_id'],
            service_id=data['service_id'],
            neighborhood_id=data['neighborhood_id'],
            date=blocked_date,
            time=time(9, 0),
            status='assigned',
        )
        db.session.add(booking)
        db.session.flush()
        db.session.add(BookingItem(
            booking_id=booking.id,
            vehicle_id=data['vehicle_id'],
            service_id=data['service_id'],
        ))
        db.session.commit()

    client = logged_in_client(app, data['customer_id'])
    days = walk_days(client, data)
    blocked = next(day for day in days if day['date'] == blocked_date)

    # That day is blocked by the single-active-booking rule, and the endpoint
    # explains why instead of just looking empty.
    assert blocked['times'] == []
    assert blocked['error'], 'the reason for the day being blocked must reach the UI'
    # The suggestion keeps scanning instead of giving up on the blocked day.
    nearest = next((day for day in days if day['times']), None)
    assert nearest is not None
    assert nearest['date'] != blocked_date


def test_booking_form_exposes_the_server_date_to_the_suggestion_box(app):
    with app.app_context():
        data = build_scenario(open_day_offsets=[0])

    client = logged_in_client(app, data['customer_id'])
    response = client.get('/customer/book')

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    # The search window must start from the server's Saudi date, not the device clock.
    assert "const serverToday = '%s'" % data['today'].isoformat() in page
