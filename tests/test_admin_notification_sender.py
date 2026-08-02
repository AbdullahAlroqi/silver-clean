from unittest.mock import patch

from app import db
from app.models import Notification, User

from test_discount_location_scope import app, login  # noqa: F401


def test_notification_sender_supports_search_filters_and_multiple_recipients(app):
    with app.app_context():
        admin = User(username='sender-admin', role='admin')
        customer = User(username='recipient-customer', role='customer', phone='0500000001')
        employee = User(username='recipient-employee', role='employee', phone='0500000002')
        db.session.add_all([admin, customer, employee])
        db.session.commit()
        admin_id, customer_id, employee_id = admin.id, customer.id, employee.id

    client = app.test_client()
    with app.app_context():
        login(client, db.session.get(User, admin_id))

    page = client.get('/admin/notifications/send')
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'id="recipient-search"' in html
    assert 'id="select-visible"' in html
    assert 'name="recipient_ids"' in html

    with patch('app.notifications.send_push_notification', return_value=True) as send_push:
        response = client.post('/admin/notifications/send', data={
            'title': 'تنبيه جماعي',
            'message': 'رسالة اختبار',
            'user_id': '0',
            'recipient_ids': [str(customer_id), str(employee_id)],
        })

    assert response.status_code == 302
    assert send_push.call_count == 2
    with app.app_context():
        notifications = Notification.query.order_by(Notification.user_id).all()
        assert {item.user_id for item in notifications} == {customer_id, employee_id}
