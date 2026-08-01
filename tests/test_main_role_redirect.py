import pytest

from app import db
from app.models import User

from test_discount_location_scope import TestConfig, app, login  # noqa: F401


@pytest.mark.parametrize(
    ('role', 'expected_location'),
    [
        ('customer', '/customer/'),
        ('employee', '/employee/'),
        ('admin', '/admin/'),
        ('supervisor', '/admin/'),
    ],
)
def test_home_redirects_authenticated_user_to_role_index(app, role, expected_location):
    with app.app_context():
        user = User(username=f'{role}-home-user', role=role)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, user_id))

    response = client.get('/')

    assert response.status_code == 302
    assert response.location.endswith(expected_location)


def test_home_remains_public_for_anonymous_visitor(app):
    response = app.test_client().get('/')

    assert response.status_code == 200
    assert 'تسجيل الدخول' in response.get_data(as_text=True)
