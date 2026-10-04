"""Every report section has to agree with the price stored on the booking.

The scenario below deliberately mixes the cases the report code used to get
wrong: a multi-vehicle order, a discounted order, a subscription wash, a
cancelled order, a booking with no area, and an overnight shift.
"""

from datetime import date, datetime, time, timedelta

import pytest
from flask import g, template_rendered

from app import db
from app.models import (Booking, BookingItem, BookingProduct, City, DiscountCode,
                        EmployeeSchedule, Neighborhood, Product, Service,
                        Subscription, SubscriptionPackage, User, Vehicle, VehicleSize)

from test_discount_location_scope import TestConfig, app, login  # noqa: F401

RANGE = 'from_date=2026-09-01&to_date=2026-09-30'


def capture(app, client, url):
    rendered = []

    def record(sender, template, context, **extra):
        rendered.append(context)

    template_rendered.connect(record, app)
    try:
        resp = client.get(url)
    finally:
        template_rendered.disconnect(record, app)
    assert resp.status_code == 200, f'{url} -> {resp.status_code}'
    return rendered[-1]


@pytest.fixture()
def world(app):
    """Seed the mixed scenario and return the ids tests need."""
    with app.app_context():
        riyadh = City(name_ar='الرياض', name_en='Riyadh', is_active=True)
        jeddah = City(name_ar='جدة', name_en='Jeddah', is_active=True)
        db.session.add_all([riyadh, jeddah])
        db.session.flush()
        n1 = Neighborhood(name_ar='حي1', name_en='N1', city_id=riyadh.id, is_active=True)
        n2 = Neighborhood(name_ar='حي2', name_en='N2', city_id=jeddah.id, is_active=True)
        admin = User(username='admin', role='admin')
        emp = User(username='emp', role='employee')
        cust = User(username='cust', role='customer')
        other = User(username='other', role='customer')
        wash = Service(name_ar='غسيل', name_en='Wash', price=100, duration=60, is_active=True)
        polish = Service(name_ar='تلميع', name_en='Polish', price=200, duration=60, is_active=True)
        product = Product(name_ar='معطر', name_en='Freshener', price=25, is_active=True)
        package = SubscriptionPackage(name_ar='شهري', name_en='Monthly', price=400,
                                      wash_count=4, duration_days=30)
        size = VehicleSize(name_ar='متوسط', name_en='Medium', price_adjustment=20, is_active=True)
        db.session.add_all([n1, n2, admin, emp, cust, other, wash, polish, product,
                            package, size])
        db.session.flush()
        supervisor = User(username='sup', role='supervisor')
        supervisor.supervisor_cities.append(riyadh)
        car1 = Vehicle(user_id=cust.id, vehicle_size_id=size.id, brand='A', plate_number='1')
        car2 = Vehicle(user_id=cust.id, vehicle_size_id=size.id, brand='B', plate_number='2')
        code = DiscountCode(code='X10', discount_type='percentage', value=10,
                            valid_until=datetime(2027, 1, 1))
        # Sep 30 2026 is a Wednesday; the night shift runs 20:00 -> 02:00.
        schedule = EmployeeSchedule(employee_id=emp.id, day_of_week=2, start_time=time(20),
                                    end_time=time(2), is_active=True)
        db.session.add_all([supervisor, car1, car2, code, schedule])
        db.session.flush()

        day = date(2026, 9, 15)

        # Single vehicle, cash: 100 service + 20 size + 2 x 25 products = 170
        plain = Booking(customer_id=cust.id, employee_id=emp.id, service_id=wash.id,
                        vehicle_id=car1.id, neighborhood_id=n1.id, date=day, time=time(10),
                        status='completed', custom_service_price=100, vehicle_size_price=20,
                        payment_method='cash', total_price=170, rating=5,
                        started_at=datetime(2026, 9, 15, 10),
                        completed_at=datetime(2026, 9, 15, 11))
        db.session.add(plain)
        db.session.flush()
        db.session.add_all([
            BookingProduct(booking_id=plain.id, product_id=product.id, quantity=2,
                           unit_price=25),
            BookingItem(booking_id=plain.id, vehicle_id=car1.id, service_id=wash.id,
                        quantity=1, service_price=100, size_price_adjustment=20,
                        total_item_price=120),
        ])

        # Two vehicles, card: 120 + 200 = 320. Only the first vehicle is
        # mirrored onto the legacy booking columns.
        multi = Booking(customer_id=cust.id, employee_id=emp.id, service_id=wash.id,
                        vehicle_id=car1.id, neighborhood_id=n1.id, date=day, time=time(12),
                        status='completed', custom_service_price=100, vehicle_size_price=20,
                        payment_method='card', is_multi_vehicle=True, total_price=320)
        db.session.add(multi)
        db.session.flush()
        db.session.add_all([
            BookingItem(booking_id=multi.id, vehicle_id=car1.id, service_id=wash.id,
                        quantity=1, service_price=100, size_price_adjustment=20,
                        total_item_price=120),
            BookingItem(booking_id=multi.id, vehicle_id=car2.id, service_id=polish.id,
                        quantity=1, service_price=200, size_price_adjustment=0,
                        total_item_price=200),
        ])

        # Cancelled, carrying the discount code, in the other city.
        db.session.add(Booking(customer_id=other.id, employee_id=emp.id, service_id=wash.id,
                               neighborhood_id=n2.id, date=day, time=time(14),
                               status='cancelled', custom_service_price=100,
                               vehicle_size_price=0, discount_code_id=code.id,
                               cancellation_reason='تأخير'))

        # Discounted 10% on a 100 service -> 90
        discounted = Booking(customer_id=other.id, employee_id=emp.id, service_id=wash.id,
                             neighborhood_id=n2.id, date=day, time=time(16),
                             status='completed', custom_service_price=100,
                             vehicle_size_price=0, discount_code_id=code.id,
                             payment_method='cash', total_price=90, rating=3)
        db.session.add(discounted)
        db.session.flush()
        db.session.add(BookingItem(booking_id=discounted.id, vehicle_id=car1.id,
                                   service_id=wash.id, quantity=1, service_price=100,
                                   size_price_adjustment=0, total_item_price=100))

        subscription = Subscription(customer_id=cust.id, neighborhood_id=n1.id,
                                    package_id=package.id, start_date=day,
                                    end_date=day + timedelta(days=30), status='active')
        db.session.add(subscription)
        db.session.flush()
        # A subscription wash earns no service revenue, only its add-on product.
        sub_wash = Booking(customer_id=cust.id, employee_id=emp.id, service_id=wash.id,
                           neighborhood_id=n1.id, date=day, time=time(18),
                           status='completed', subscription_id=subscription.id,
                           vehicle_size_price=0, payment_method='cash', total_price=25)
        db.session.add(sub_wash)
        db.session.flush()
        db.session.add(BookingProduct(booking_id=sub_wash.id, product_id=product.id,
                                      quantity=1, unit_price=25))

        db.session.add(Subscription(customer_id=other.id, neighborhood_id=n2.id,
                                    package_id=package.id, start_date=day,
                                    end_date=day + timedelta(days=30), status='active'))
        db.session.commit()
        return {
            'admin': admin.id, 'supervisor': supervisor.id, 'employee': emp.id,
            'customer': cust.id, 'riyadh': riyadh.id, 'jeddah': jeddah.id,
            'n1': n1.id, 'n2': n2.id, 'code': code.id,
        }


def client_for(app, user_id):
    # The app fixture keeps a single app context alive for the whole test and
    # Flask-Login caches the resolved user on it, so drop that cache or a
    # second client would silently keep acting as the first user.
    g.pop('_login_user', None)
    client = app.test_client()
    login(client, db.session.get(User, user_id))
    return client


# --- التقارير (/admin/reports) ---------------------------------------------

def test_reports_revenue_counts_every_vehicle_and_reconciles(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/reports?' + RANGE)

    # 120 (plain) + 320 (multi-vehicle) + 90 (discounted) + 0 (subscription wash)
    assert ctx['service_revenue'] == 530
    # 2 x 25 on the plain booking + 1 x 25 on the subscription wash
    assert ctx['product_revenue'] == 75
    assert ctx['subscription_revenue'] == 800
    assert ctx['total_revenue'] == 530 + 75 + 800

    # The payment mix has to account for exactly the booking revenue.
    assert ctx['cash_total'] + ctx['card_total'] == ctx['service_revenue'] + ctx['product_revenue']
    assert ctx['cash_count'] + ctx['card_count'] == ctx['completed_bookings']
    assert ctx['card_total'] == 320

    # The city table has to account for every riyal on the page.
    assert sum(row['revenue'] for row in ctx['city_performance'].values()) == ctx['total_revenue']
    assert sum(row['count'] for row in ctx['city_performance'].values()) == ctx['completed_bookings']


def test_reports_top_services_include_secondary_vehicles(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/reports?' + RANGE)
    counts = dict(ctx['top_services'])
    assert counts.get('تلميع') == 1, 'the second vehicle of a multi-vehicle order was dropped'
    # One wash each on the plain, multi-vehicle, cancelled, discounted and
    # subscription bookings.
    assert counts.get('غسيل') == 5


def test_reports_city_filter_narrows_subscriptions_too(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/reports?%s&city_id=%d' % (RANGE, world['riyadh']))

    # One subscription in Riyadh, priced at 400 - the count and the revenue
    # have to describe the same set of rows.
    assert ctx['active_subscriptions'] == 1
    assert ctx['subscription_revenue'] == 400
    assert set(ctx['city_performance']) == {'الرياض'}


def test_reports_neighborhood_filter_keeps_its_dropdown(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/reports?%s&neighborhood_id=%d' % (RANGE, world['n1']))
    assert ctx['neighborhood_id'] == world['n1']
    assert ctx['city_id'] == world['riyadh'], 'the parent city should be selected as well'
    assert [n.id for n in ctx['neighborhoods']] == [world['n1']]


def test_reports_include_bookings_without_an_area(world, app):
    with app.app_context():
        service = Service.query.filter_by(name_en='Wash').first()
        db.session.add(Booking(customer_id=world['customer'], service_id=service.id,
                               neighborhood_id=None, date=date(2026, 9, 20), time=time(9),
                               status='completed', custom_service_price=60,
                               vehicle_size_price=0, payment_method='cash', total_price=60))
        db.session.commit()

    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/reports?' + RANGE)
    assert ctx['service_revenue'] == 530 + 60
    assert 'غير محدد' in ctx['city_performance']


# --- التقارير الإدارية (/admin/management-reports) --------------------------

def test_management_reports_match_the_operational_report(world, app):
    client = client_for(app, world['admin'])
    operational = capture(app, client, '/admin/reports?' + RANGE)
    management = capture(app, client, '/admin/management-reports?' + RANGE)
    assert management['total'] == operational['total_bookings']
    assert management['completed'] == operational['completed_bookings']
    assert sum(row['total'] for row in management['city_stats']) == management['total']


def test_management_service_stats_include_secondary_vehicles(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/management-reports?' + RANGE)
    counts = {row['name']: row['count'] for row in ctx['service_stats']}
    assert counts.get('تلميع') == 1


def test_management_expiring_subscriptions_follow_the_city_filter(world, app):
    with app.app_context():
        package = SubscriptionPackage.query.first()
        today = date.today()
        db.session.add(Subscription(customer_id=world['customer'], neighborhood_id=world['n2'],
                                    package_id=package.id,
                                    start_date=today - timedelta(days=27),
                                    end_date=today + timedelta(days=3), status='active'))
        db.session.commit()

    client = client_for(app, world['admin'])
    assert capture(app, client, '/admin/management-reports')['expiring_subscriptions'] == 1
    riyadh = capture(app, client, '/admin/management-reports?city_id=%d' % world['riyadh'])
    assert riyadh['expiring_subscriptions'] == 0, 'Riyadh has nothing expiring'


def test_both_pages_attribute_overnight_work_to_the_shift_that_started_it(world, app):
    """A 01:30 booking on Oct 1 belongs to the Sep 30 night shift."""
    with app.app_context():
        service = Service.query.filter_by(name_en='Wash').first()
        db.session.add(Booking(customer_id=world['customer'], employee_id=world['employee'],
                               service_id=service.id, neighborhood_id=world['n1'],
                               date=date(2026, 10, 1), time=time(1, 30), status='completed',
                               custom_service_price=50, vehicle_size_price=0,
                               payment_method='cash', total_price=50))
        db.session.commit()

    client = client_for(app, world['admin'])
    operational = capture(app, client, '/admin/reports?' + RANGE)
    management = capture(app, client, '/admin/management-reports?' + RANGE)
    assert operational['service_revenue'] == 530 + 50
    assert management['total'] == operational['total_bookings']


# --- Filter input handling -------------------------------------------------

@pytest.mark.parametrize('query', [
    'from_date=abc&to_date=2026-09-30',
    'from_date=2026-13-45&to_date=',
    'from_date=2026-09-30&to_date=2026-09-01',
])
def test_report_pages_survive_odd_date_input(world, app, query):
    client = client_for(app, world['admin'])
    capture(app, client, '/admin/reports?' + query)
    capture(app, client, '/admin/management-reports?' + query)


def test_reversed_range_is_read_as_a_range(world, app):
    client = client_for(app, world['admin'])
    forward = capture(app, client, '/admin/reports?' + RANGE)
    reversed_ = capture(app, client, '/admin/reports?from_date=2026-09-30&to_date=2026-09-01')
    assert reversed_['total_bookings'] == forward['total_bookings']


# --- Supervisor scoping ----------------------------------------------------

def test_supervisor_reports_stay_inside_the_assigned_city(world, app):
    client = client_for(app, world['supervisor'])
    ctx = capture(app, client, '/admin/reports?' + RANGE)
    assert ctx['service_revenue'] == 440          # 120 + 320, Riyadh only
    assert ctx['active_subscriptions'] == 1
    assert ctx['subscription_revenue'] == 400
    assert [c.id for c in ctx['cities']] == [world['riyadh']]

    forced_city = capture(app, client,
                          '/admin/reports?%s&city_id=%d' % (RANGE, world['jeddah']))
    assert forced_city['city_id'] is None
    assert forced_city['service_revenue'] == 440

    forced_area = capture(app, client,
                          '/admin/reports?%s&neighborhood_id=%d' % (RANGE, world['n2']))
    assert forced_area['neighborhood_id'] is None
    assert forced_area['city_id'] is None
    assert forced_area['service_revenue'] == 440


# --- Per-entity stats sections --------------------------------------------

def test_employee_stats_earnings_cover_every_vehicle(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/employees/%d/stats?%s' % (world['employee'], RANGE))
    stats = ctx['stats']
    # 170 (plain) + 320 (multi) + 90 (discounted) + 25 (subscription add-on)
    assert stats['total_earnings'] == 605
    assert stats['card_earnings'] == 320
    assert stats['cash_earnings'] == 170 + 90 + 25
    assert stats['subscription_bookings_count'] == 1


def test_customer_stats_spend_uses_the_price_actually_charged(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/customers/%d/stats' % world['customer'])
    stats = ctx['stats']
    # Plain 120 + multi-vehicle 320; the subscription wash itself is free.
    assert stats['total_services_value'] == 440
    assert stats['total_products_value'] == 75
    assert stats['total_products_purchased'] == 3
    assert stats['total_spent'] == 515


def test_discount_savings_ignore_cancelled_orders(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/discount_codes/stats/%d' % world['code'])
    # The code sits on two bookings but only the completed one saved anything:
    # 10% of a 100 service.
    assert ctx['total_savings'] == 10


# --- الشاشة الرئيسية and the other revenue columns ------------------------

def test_dashboard_revenue_is_what_was_charged(world, app):
    """The dashboard card must not price yesterday's work at today's rates."""
    with app.app_context():
        # Catalogue price moves after the fact; takings must not move with it.
        Service.query.filter_by(name_en='Wash').first().price = 999
        db.session.commit()

    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/?date=2026-09-15')
    # 170 (plain) + 320 (multi) + 90 (discounted) + 25 (subscription add-on)
    assert ctx['total_revenue'] == 605


def test_locations_revenue_is_what_was_charged(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/locations')
    by_city = {row['city'].name_ar: row['revenue'] for row in ctx['city_stats']}
    assert by_city['الرياض'] == 170 + 320 + 25
    assert by_city['جدة'] == 90


def test_seasons_revenue_is_what_was_charged(world, app):
    with app.app_context():
        from app.models import Season
        db.session.add(Season(name_ar='موسم', name_en='Season', is_active=True,
                              start_date=date(2026, 9, 1), end_date=date(2026, 9, 30)))
        db.session.commit()

    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/seasons')
    assert ctx['seasons'][0].total_revenue == 605


def test_services_revenue_counts_secondary_vehicles(world, app):
    client = client_for(app, world['admin'])
    ctx = capture(app, client, '/admin/services')
    rows = {row['service'].name_en: row for row in ctx['services']}

    # Polish was only ever sold as the second vehicle of a multi-vehicle order.
    assert rows['Polish']['completed_bookings_count'] == 1
    assert rows['Polish']['total_revenue'] == 200

    # Wash: plain 120 + multi 120 + discounted 90 + subscription wash 0
    assert rows['Wash']['completed_bookings_count'] == 4
    assert rows['Wash']['total_revenue'] == 330

    # Per-service revenue must add up to the page-level service revenue.
    operational = capture(app, client, '/admin/reports?' + RANGE)
    assert sum(row['total_revenue'] for row in ctx['services']) == operational['service_revenue']


def test_employee_own_stats_match_the_admin_view(world, app):
    admin_ctx = capture(app, client_for(app, world['admin']),
                        '/admin/employees/%d/stats' % world['employee'])
    own_ctx = capture(app, client_for(app, world['employee']), '/employee/stats')
    assert own_ctx['total_earnings'] == admin_ctx['stats']['total_earnings']
    assert own_ctx['total_products_revenue'] == 75
    assert own_ctx['total_services_revenue'] == 530
