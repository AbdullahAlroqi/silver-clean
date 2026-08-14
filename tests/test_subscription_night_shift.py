from datetime import time, timedelta

from app import db
from app.models import (
    Booking, City, EmployeeSchedule, Neighborhood, Service,
    Subscription, User, Vehicle,
)
from app.utils.timezone import get_saudi_date

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def test_subscription_can_book_an_available_time_after_midnight(app):
    work_date = get_saudi_date() + timedelta(days=1)

    with app.app_context():
        customer = User(username='night-subscription-customer', role='customer')
        employee = User(username='night-subscription-employee', role='employee')
        city = City(name_ar='مدينة الاختبار')
        neighborhood = Neighborhood(name_ar='حي الاختبار', city=city)
        service = Service(name_ar='غسيل', duration=60, is_active=True)
        db.session.add_all([customer, employee, city, neighborhood, service])
        db.session.flush()

        neighborhood.employees.append(employee)
        vehicle = Vehicle(user_id=customer.id, brand='Test', plate_number='1234')
        db.session.add(vehicle)
        db.session.flush()
        subscription = Subscription(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            neighborhood_id=neighborhood.id,
            remaining_washes=2,
            status='active',
        )
        schedule = EmployeeSchedule(
            employee_id=employee.id,
            day_of_week=work_date.weekday(),
            start_time=time(22, 0),
            end_time=time(2, 0),
            is_active=True,
        )
        db.session.add_all([subscription, schedule])
        db.session.commit()
        customer_id = customer.id
        subscription_id = subscription.id
        employee_id = employee.id
        city_id = city.id
        neighborhood_id = neighborhood.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    response = client.post(
        f'/customer/subscription/{subscription_id}/book',
        data={
            'date': work_date.isoformat(),
            'time': '00:30',
            'city_id': str(city_id),
            'neighborhood_id': str(neighborhood_id),
            'location_lat': '24.0',
            'location_lng': '46.0',
        },
    )

    assert response.status_code == 302
    assert '/customer/subscription/booking-success/' in response.headers['Location']
    with app.app_context():
        booking = Booking.query.filter_by(subscription_id=subscription_id).one()
        assert booking.employee_id == employee_id
        assert booking.date == work_date + timedelta(days=1)
        assert booking.time == time(0, 30)
