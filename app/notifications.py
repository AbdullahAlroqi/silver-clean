import json
from pywebpush import webpush, WebPushException
from app.models import PushSubscription

# VAPID keys for Web Push
VAPID_PRIVATE_KEY = "ihwqu8ewAWxBRs8J85o6g8VO9FG5RK8kCLUzB2qvqr0"
VAPID_PUBLIC_KEY = "BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c"
VAPID_EMAIL = "mailto:admin@silverclean.com"

import threading
from flask import current_app
from app import create_app, db

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
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": VAPID_EMAIL
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
