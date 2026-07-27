from datetime import date, time

from flask import template_rendered

from app import db
from app.models import Booking, EmployeeSchedule
from app.utils.shift_utils import get_booking_work_date

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


def test_after_midnight_booking_belongs_to_previous_overnight_workday():
    schedule = EmployeeSchedule(
        day_of_week=0, start_time=time(20, 0), end_time=time(2, 0), is_active=True
    )
    during_shift = Booking(date=date(2026, 7, 28), time=time(1, 30))
    after_shift = Booking(date=date(2026, 7, 28), time=time(3, 0))

    assert get_booking_work_date(during_shift, [schedule]) == date(2026, 7, 27)
    assert get_booking_work_date(after_shift, [schedule]) == date(2026, 7, 28)


def test_dashboard_total_excludes_cancelled_bookings(app):
    from app.models import Service, User

    with app.app_context():
        admin = User(username='admin', role='admin')
        customer = User(username='customer', role='customer')
        service = Service(name_ar='غسيل', name_en='Wash', price=50, duration=30)
        db.session.add_all([admin, customer, service])
        db.session.flush()
        db.session.add_all([
            Booking(customer_id=customer.id, service_id=service.id,
                    date=date(2026, 7, 27), time=time(10), status='completed'),
            Booking(customer_id=customer.id, service_id=service.id,
                    date=date(2026, 7, 27), time=time(11), status='cancelled'),
        ])
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    rendered = []
    def record_template(sender, template, context, **extra):
        rendered.append(context)

    template_rendered.connect(record_template, app)
    try:
        response = client.get('/admin/?date=2026-07-27')
    finally:
        template_rendered.disconnect(record_template, app)

    assert response.status_code == 200
    assert rendered[-1]['bookings_count'] == 1
