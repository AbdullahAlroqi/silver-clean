import json
from pywebpush import webpush, WebPushException
from app.models import PushSubscription

import threading
from flask import current_app
from app import db

def _send_async(app, user_id, notification_data, subscription_data):
    """Background task to send notifications and clean up invalid subscriptions"""
    # Create a new app context for the thread
    with app.app_context():
        # Re-query user to ensure we have a fresh session if needed, 
        # though here we are using passed subscription data for sending
        # We need the DB mainly for deleting invalid subs
        
        success_count = 0
        from app.models import PushSubscription
        
        for sub_info in subscription_data:
            sid = sub_info['id']
            # Prepare data for webpush
            push_info = {
                "endpoint": sub_info['endpoint'],
                "keys": {
                    "p256dh": sub_info['p256dh'],
                    "auth": sub_info['auth']
                }
            }
            
            try:
                webpush(
                    subscription_info=push_info,
                    data=json.dumps(notification_data),
                    vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                    vapid_claims={
                        "sub": app.config['VAPID_CLAIM_EMAIL']
                    }
                )
                success_count += 1
            except WebPushException as ex:
                # print(f"Push failed: {ex}")
                # Remove invalid subscription if status is 400 (Bad Request), 404 (Not Found), or 410 (Gone)
                if ex.response is not None and ex.response.status_code in [400, 404, 410]:
                    try:
                        # Fetch the specific subscription record to delete it
                        # We use the ID passed from the main thread
                        subscription_to_delete = PushSubscription.query.get(sid)
                        if subscription_to_delete:
                            print(f"Removing invalid subscription {sid} (Status {ex.response.status_code})")
                            db.session.delete(subscription_to_delete)
                            db.session.commit()
                    except Exception as db_ex:
                        print(f"Error removing subscription: {db_ex}")

def send_push_notification(user, notification_data):
    """Send PWA push notification to a user (asynchronously)"""
    subscriptions = user.push_subscriptions
    
    if not subscriptions:
        print(f"⚠️ User {user.username} has no push subscriptions")
        return False
        
    # extract necessary data to pass to thread (avoid detached instance errors)
    subscription_data = []
    for sub in subscriptions:
        subscription_data.append({
            'id': sub.id,
            'endpoint': sub.endpoint,
            'p256dh': sub.p256dh,
            'auth': sub.auth
        })
    
    # Get the real app object (not the proxy) to pass to the thread
    app = current_app._get_current_object()
    
    # Start background thread
    thread = threading.Thread(
        target=_send_async,
        args=(app, user.id, notification_data, subscription_data)
    )
    thread.daemon = True # Daemonize thread so it doesn't block app shutdown
    thread.start()
            
    return True # We return True immediately as we can't wait for the result


def notify_area_supervisors(neighborhood_id=None, city_id=None, event_type='request',
                            object_id=None, customer_name=None):
    """Notify only supervisors explicitly assigned to the request's city or neighborhood."""
    from app import db
    from app.models import City, Neighborhood, Notification

    neighborhood = Neighborhood.query.get(neighborhood_id) if neighborhood_id else None
    if neighborhood:
        city_id = neighborhood.city_id
    city = City.query.get(city_id) if city_id else None

    supervisors = {}
    if neighborhood:
        for supervisor in neighborhood.supervisors.filter_by(role='supervisor').all():
            supervisors[supervisor.id] = supervisor
    if city:
        for supervisor in city.supervisors.filter_by(role='supervisor').all():
            supervisors[supervisor.id] = supervisor

    if not supervisors:
        return 0

    event_labels = {
        'booking': ('حجز جديد', '/admin/bookings'),
        'subscription': ('طلب اشتراك جديد', '/admin/subscriptions'),
        'subscription_booking': ('حجز اشتراك جديد', '/admin/bookings'),
        'gift': ('طلب هدية جديد', '/admin/gift-orders'),
        'polishing': ('طلب تلميع جديد', '/admin/polishing-orders'),
    }
    title, url = event_labels.get(event_type, ('طلب جديد', '/admin/'))
    area_name = ' - '.join(filter(None, [
        city.name_ar if city else None,
        neighborhood.name_ar if neighborhood else None
    ]))
    details = [f'رقم الطلب: {object_id}' if object_id else None,
               f'العميل: {customer_name}' if customer_name else None,
               f'المنطقة: {area_name}' if area_name else None]
    message = ' | '.join(item for item in details if item)

    for supervisor in supervisors.values():
        db.session.add(Notification(
            user_id=supervisor.id,
            title=title,
            message=message
        ))
    db.session.commit()

    payload = {
        'title': title,
        'body': message,
        'icon': '/static/images/logo.png',
        'badge': '/static/images/logo.png',
        'url': url,
        'data': {'event_type': event_type, 'object_id': object_id}
    }
    for supervisor in supervisors.values():
        send_push_notification(supervisor, payload)
    return len(supervisors)
