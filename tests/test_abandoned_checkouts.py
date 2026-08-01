from datetime import datetime, timedelta

from flask import template_rendered

from app import db
from app.models import Booking, CheckoutSession, City, DiscountCode, Neighborhood, User

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


def test_repeated_abandoned_checkouts_are_grouped_under_one_customer(app):
    with app.app_context():
        admin = User(username='group-admin', role='admin')
        customer = User(username='group-customer', role='customer')
        db.session.add_all([admin, customer])
        db.session.flush()
        old = datetime.utcnow() - timedelta(minutes=45)
        db.session.add_all([
            CheckoutSession(
                token='group-cart-one', customer_id=customer.id,
                flow_type='booking', page_name='المحاولة الأولى',
                status='active', last_activity_at=old
            ),
            CheckoutSession(
                token='group-cart-two', customer_id=customer.id,
                flow_type='polishing', page_name='المحاولة الثانية',
                status='active', last_activity_at=old + timedelta(minutes=1)
            ),
        ])
        recovery_code = DiscountCode(
            code='BACKUSED1', discount_type='percentage', value=10,
            valid_until=datetime.utcnow() + timedelta(days=7), is_active=True
        )
        db.session.add(recovery_code)
        db.session.flush()
        db.session.add(Booking(
            customer_id=customer.id, status='completed',
            discount_code_id=recovery_code.id
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
        response = client.get('/admin/abandoned-checkouts')
    finally:
        template_rendered.disconnect(record_template, app)

    assert response.status_code == 200
    assert len(rendered[-1]['rows']) == 1
    assert rendered[-1]['rows'][0]['attempts_count'] == 2
    assert rendered[-1]['rows'][0]['used_recovery_discount'] is True
    page = response.get_data(as_text=True)
    assert 'المحاولة الأولى' in page
    assert 'المحاولة الثانية' in page
    assert 'استفاد سابقًا من كود استعادة' in page


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


def test_admin_can_create_one_use_discount_for_abandoned_checkout(app):
    with app.app_context():
        admin = User(username='admin', role='admin')
        customer = User(username='customer', phone='0500000000', role='customer')
        city = City(name_ar='الرياض')
        db.session.add_all([admin, customer, city])
        db.session.flush()
        neighborhood = Neighborhood(name_ar='العليا', city_id=city.id)
        db.session.add(neighborhood)
        db.session.flush()
        checkout = CheckoutSession(
            token='recover-cart', customer_id=customer.id, flow_type='booking',
            page_name='حجز خدمة', status='active', city_id=city.id,
            neighborhood_id=neighborhood.id,
            last_activity_at=datetime.utcnow() - timedelta(minutes=40)
        )
        db.session.add(checkout)
        db.session.commit()
        admin_id = admin.id
        checkout_id = checkout.id
        neighborhood_id = neighborhood.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))
    response = client.post(
        f'/admin/abandoned-checkouts/{checkout_id}/create-discount',
        data={'discount_type': 'percentage', 'value': '15'},
        follow_redirects=True
    )

    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert 'حجز خدمة' in response_text
    assert 'https://wa.me/966500000000?text=' in response_text
    assert '%0A' in response_text
    with app.app_context():
        code = DiscountCode.query.one()
        assert code.value == 15
        assert code.usage_limit == 1
        assert code.max_uses_per_customer == 1
        assert code.is_active is True
        assert code.valid_from <= datetime.utcnow() <= code.valid_until
        assert code.neighborhood_id == neighborhood_id
        checkout = db.session.get(CheckoutSession, checkout_id)
        assert code.scope_label == 'الرياض - العليا'
        assert code.assigned_customer_id == checkout.customer_id
        assert code.is_available_to(checkout.customer)
        assert not code.is_available_to(User(username='different-customer', role='customer'))
        assert checkout.recovery_discount_code_id == code.id
        assert checkout.last_activity_at <= datetime.utcnow() - timedelta(minutes=30)

        # A recovery-code cart remains listed even if another update touches its timestamp.
        checkout.last_activity_at = datetime.utcnow()
        db.session.commit()
    page = client.get('/admin/abandoned-checkouts')
    assert 'حجز خدمة' in page.get_data(as_text=True)

    response = client.post(
        f'/admin/abandoned-checkouts/{checkout_id}/delete-discount',
        follow_redirects=True
    )
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert 'حجز خدمة' in response_text
    assert 'https://wa.me/966500000000?text=' in response_text
    assert '%0A' in response_text
    with app.app_context():
        assert DiscountCode.query.count() == 0
        checkout = db.session.get(CheckoutSession, checkout_id)
        assert checkout.recovery_discount_code_id is None
        assert checkout.last_activity_at <= datetime.utcnow() - timedelta(minutes=30)


def test_abandoned_checkout_is_deleted_after_two_days(app):
    with app.app_context():
        customer = User(username='expired-cart-customer', role='customer')
        db.session.add(customer)
        db.session.flush()
        checkout = CheckoutSession(
            token='expired-resume-cart', customer_id=customer.id,
            flow_type='booking', page_name='حجز منتهي', status='active',
            created_at=datetime.utcnow() - timedelta(days=2, minutes=1),
            last_activity_at=datetime.utcnow() - timedelta(days=2, minutes=1)
        )
        db.session.add(checkout)
        db.session.commit()
        customer_id = customer.id
        checkout_id = checkout.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    response = client.get('/customer/')
    assert response.status_code == 200
    assert 'expired-resume-cart' not in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(CheckoutSession, checkout_id) is None


def test_reopening_checkout_does_not_refresh_admin_activity_timer(app):
    with app.app_context():
        customer = User(username='reopen-customer', role='customer')
        db.session.add(customer)
        db.session.flush()
        old_activity = datetime.utcnow() - timedelta(minutes=45)
        checkout = CheckoutSession(
            token='reopen-existing-cart', customer_id=customer.id,
            flow_type='booking', page_name='حجز قائم', status='active',
            last_activity_at=old_activity
        )
        db.session.add(checkout)
        db.session.commit()
        customer_id = customer.id
        checkout_id = checkout.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    response = client.post('/customer/api/checkout-progress', json={
        'token': 'reopen-existing-cart',
        'flow_type': 'booking',
        'page_name': 'حجز قائم',
        'step_name': 'الخطوة 1 من 4',
        'form_data': {},
        'initial_load': True
    })
    assert response.status_code == 200
    with app.app_context():
        checkout = db.session.get(CheckoutSession, checkout_id)
        assert checkout.last_activity_at == old_activity


def test_other_customer_sees_arabic_message_for_assigned_recovery_code(app):
    with app.app_context():
        owner = User(username='code-owner', role='customer')
        other_customer = User(username='code-other-customer', role='customer')
        db.session.add_all([owner, other_customer])
        db.session.flush()
        code = DiscountCode(
            code='BACKOWNER1', discount_type='percentage', value=10,
            valid_until=datetime.utcnow() + timedelta(days=7),
            is_active=True, assigned_customer_id=owner.id
        )
        db.session.add(code)
        db.session.commit()
        other_customer_id = other_customer.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, other_customer_id))

    response = client.post(
        '/customer/api/verify-discount',
        json={'code': 'BACKOWNER1'}
    )
    assert response.status_code == 200
    assert response.get_json() == {
        'valid': False,
        'message': 'هذا الكود مخصص لعميل آخر'
    }
