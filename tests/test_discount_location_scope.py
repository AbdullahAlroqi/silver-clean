from datetime import datetime, timedelta

import pytest

from app import create_app, db
from app.models import City, DiscountCode, Neighborhood, User


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    MAIL_SUPPRESS_SEND = True


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def login(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def test_supervisor_can_only_create_discount_in_assigned_scope(app):
    with app.app_context():
        assigned_city = City(name_ar='الرياض', name_en='Riyadh')
        other_city = City(name_ar='جدة', name_en='Jeddah')
        db.session.add_all([assigned_city, other_city])
        db.session.flush()
        supervisor = User(username='supervisor', role='supervisor')
        supervisor.supervisor_cities.append(assigned_city)
        db.session.add(supervisor)
        db.session.commit()
        supervisor_id = supervisor.id
        assigned_city_id = assigned_city.id
        other_city_id = other_city.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, supervisor_id))

    common = {
        'discount_type': 'percentage',
        'value': '10',
        'valid_until': (datetime.utcnow() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'scope_type': 'city',
    }
    response = client.post(
        '/admin/discount_codes/add',
        data={**common, 'code': 'RIYADH10', 'city_id': str(assigned_city_id)},
    )
    assert response.status_code == 302

    response = client.post(
        '/admin/discount_codes/add',
        data={**common, 'code': 'JEDDAH10', 'city_id': str(other_city_id)},
    )
    assert response.status_code == 200
    with app.app_context():
        assert DiscountCode.query.filter_by(code='RIYADH10', created_by_id=supervisor_id).count() == 1
        assert DiscountCode.query.filter_by(code='JEDDAH10').count() == 0


def test_location_scoped_code_only_applies_to_matching_neighborhood(app):
    with app.app_context():
        city = City(name_ar='الرياض', name_en='Riyadh')
        other_city = City(name_ar='جدة', name_en='Jeddah')
        db.session.add_all([city, other_city])
        db.session.flush()
        matching = Neighborhood(name_ar='العليا', city_id=city.id)
        other = Neighborhood(name_ar='الروضة', city_id=other_city.id)
        code = DiscountCode(
            code='LOCAL10', discount_type='percentage', value=10,
            valid_until=datetime.utcnow() + timedelta(days=10), city_id=city.id
        )
        db.session.add_all([matching, other, code])
        db.session.commit()
        assert code.applies_to(matching)
        assert not code.applies_to(other)


def test_customer_cannot_verify_code_after_switching_to_another_city(app):
    with app.app_context():
        customer = User(username='location-customer', role='customer')
        city = City(name_ar='الرياض')
        other_city = City(name_ar='جدة')
        db.session.add_all([customer, city, other_city])
        db.session.flush()
        matching = Neighborhood(name_ar='العليا', city_id=city.id)
        other = Neighborhood(name_ar='الروضة', city_id=other_city.id)
        db.session.add_all([matching, other])
        db.session.flush()
        code = DiscountCode(
            code='CITYONLY10', discount_type='percentage', value=10,
            valid_until=datetime.utcnow() + timedelta(days=7),
            is_active=True, city_id=city.id, assigned_customer_id=customer.id
        )
        db.session.add(code)
        db.session.commit()
        customer_id = customer.id
        other_neighborhood_id = other.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, customer_id))

    response = client.post('/customer/api/verify-discount', json={
        'code': 'CITYONLY10',
        'neighborhood_id': other_neighborhood_id
    })
    assert response.status_code == 200
    assert response.get_json() == {
        'valid': False,
        'message': 'كود الخصم غير متاح في المدينة أو الحي المحدد'
    }
