from datetime import date, time

from flask import template_rendered

from app import db
from app.models import Booking, City, EmployeeSchedule, Neighborhood
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


def test_dashboard_groups_after_midnight_booking_with_previous_shift(app):
    from app.models import Service, User

    with app.app_context():
        admin = User(username='admin', role='admin')
        employee = User(username='employee', role='employee')
        customer = User(username='customer', role='customer')
        service = Service(name_ar='غسيل', name_en='Wash', price=50, duration=30)
        db.session.add_all([admin, employee, customer, service])
        db.session.flush()
        db.session.add(EmployeeSchedule(
            employee_id=employee.id, day_of_week=3,
            start_time=time(20), end_time=time(2), is_active=True
        ))
        db.session.add(Booking(
            customer_id=customer.id, employee_id=employee.id, service_id=service.id,
            date=date(2026, 7, 31), time=time(1), status='completed'
        ))
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
        response = client.get('/admin/?date=2026-07-30')
    finally:
        template_rendered.disconnect(record_template, app)

    assert response.status_code == 200
    assert rendered[-1]['bookings_count'] == 1
    assert rendered[-1]['total_revenue'] == 50


def test_reports_group_after_midnight_completion_with_previous_shift(app):
    from app.models import Service, User

    with app.app_context():
        admin = User(username='admin', role='admin')
        employee = User(username='employee', role='employee')
        customer = User(username='customer', role='customer')
        city = City(name_ar='الرياض')
        service = Service(name_ar='غسيل', name_en='Wash', price=75, duration=30)
        db.session.add_all([admin, employee, customer, city, service])
        db.session.flush()
        neighborhood = Neighborhood(name_ar='العليا', city_id=city.id)
        db.session.add(neighborhood)
        db.session.flush()
        db.session.add(EmployeeSchedule(
            employee_id=employee.id, day_of_week=3,
            start_time=time(20), end_time=time(2), is_active=True
        ))
        db.session.add(Booking(
            customer_id=customer.id, employee_id=employee.id,
            service_id=service.id, neighborhood_id=neighborhood.id,
            date=date(2026, 7, 31), time=time(1), status='completed',
            payment_method='cash'
        ))
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
        response = client.get(
            '/admin/reports?from_date=2026-07-30&to_date=2026-07-30'
        )
    finally:
        template_rendered.disconnect(record_template, app)

    assert response.status_code == 200
    context = rendered[-1]
    assert context['total_bookings'] == 1
    assert context['completed_bookings'] == 1
    assert context['cash_count'] == 1
    assert context['service_revenue'] == 75
    assert context['employee_stats'][0]['completed'] == 1
    assert context['employee_stats'][0]['total'] == 1
    assert context['top_services'][0][1] == 1
    assert b'employee' in response.data


def test_management_reports_page_renders_operational_metrics(app):
    from app.models import Service, User

    with app.app_context():
        admin = User(username='reports-admin', role='admin')
        employee = User(username='reports-employee', role='employee')
        customer = User(username='reports-customer', role='customer')
        city = City(name_ar='مدينة الاختبار')
        service = Service(name_ar='غسيل اختباري', name_en='Test wash', price=50, duration=30)
        db.session.add_all([admin, employee, customer, city, service])
        db.session.flush()
        neighborhood = Neighborhood(name_ar='حي الاختبار', city_id=city.id)
        db.session.add(neighborhood)
        db.session.flush()
        db.session.add(Booking(
            customer_id=customer.id, employee_id=employee.id, service_id=service.id,
            neighborhood_id=neighborhood.id, date=date(2026, 7, 30),
            time=time(10), status='completed', rating=5
        ))
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    response = client.get('/admin/management-reports?from_date=2026-07-30&to_date=2026-07-30')

    assert response.status_code == 200
    assert 'التقارير الإدارية' in response.get_data(as_text=True)
    assert 'reports-employee' in response.get_data(as_text=True)
    assert 'غسيل اختباري' in response.get_data(as_text=True)
