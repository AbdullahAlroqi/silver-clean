import json
from pywebpush import webpush, WebPushException
from app.models import PushSubscription

# VAPID keys for Web Push
VAPID_PRIVATE_KEY = "ihwqu8ewAWxBRs8J85o6g8VO9FG5RK8kCLUzB2qvqr0"
VAPID_PUBLIC_KEY = "BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c"
VAPID_EMAIL = "mailto:admin@silverclean.com"

def send_push_notification(user, notification_data):
    """Send PWA push notification to a user (employee or customer)"""
    subscriptions = user.push_subscriptions
    
    if not subscriptions:
        print(f"⚠️ User {user.username} has no push subscriptions")
        return False
        
    success_count = 0
    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth
            }
        }
        
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_EMAIL
                }
            )
            success_count += 1
        except WebPushException as ex:
            print(f"Push notification failed for {user.username}: {ex}")
            # Optional: Remove invalid subscription
            # if ex.response.status_code == 410:
            #     db.session.delete(sub)
            #     db.session.commit()
            
    return success_count > 0
