"""
Booking Notification System with PWA Push Notifications
Sends notifications to employees 10 minutes before their next booking
"""
from app import create_app, db
from app.models import Booking, User
from datetime import datetime, timedelta
import time
import json
from pywebpush import webpush, WebPushException

app = create_app()

from app.notifications import send_push_notification

def notify_employee(employee, booking):
    """Send notification to employee via PWA push notification"""
    print(f"📢 إشعار للموظف {employee.username}:")
    print(f"   الحجز #{booking.id} يبدأ بعد 10 دقائق!")
    print(f"   العميل: {booking.customer.username} - {booking.customer.phone}")
    print(f"   الموعد: {booking.date} {booking.time}")
    print(f"   المركبة: {booking.vehicle.brand} - {booking.vehicle.plate_number}")
    print(f"   الخدمة: {booking.service.name_ar}")
    
    # Calculate total price
    products_total = sum([bp.product.price * bp.quantity for bp in booking.products])
    grand_total = booking.service.price + products_total
    
    # Prepare notification data
    notification_data = {
        "title": "🔔  حجز قادم بعد 10 دقائق!",
        "body": f"العميل: {booking.customer.username}\nالخدمة: {booking.service.name_ar}\nالمركبة: {booking.vehicle.brand}\nالمجموع: {grand_total} ريال",
        "icon": "/static/images/logo.png",
        "badge": "/static/images/logo.png",
        "url": f"/employee/bookings/active",
        "data": {
            "booking_id": booking.id,
            "customer_name": booking.customer.username,
            "customer_phone": booking.customer.phone,
            "vehicle": f"{booking.vehicle.brand} - {booking.vehicle.plate_number}",
            "service": booking.service.name_ar,
            "total": grand_total,
            "time": booking.time.strftime('%H:%M') if booking.time else ''
        }
    }
    
    # Send notification using shared utility
    success = send_push_notification(employee, notification_data)
    
    if success:
        print("✅ تم إرسال الإشعار بنجاح!")
    else:
        print("⚠️ الموظف لم يفعّل الإشعارات على جهازه أو فشل الإرسال")
    
    print("-" * 50)

def check_upcoming_bookings():
    """Check for bookings starting in 10 minutes"""
    with app.app_context():
        # Get current time + 10 minutes
        target_time = datetime.now() + timedelta(minutes=10)
        target_date = target_time.date()
        
        # Find bookings that start around this time (within 1 minute window)
        bookings = Booking.query.filter(
            Booking.date == target_date,
            Booking.status == 'assigned',
            Booking.employee_id.isnot(None)
        ).all()
        
        for booking in bookings:
            if booking.time:
                # Check if booking time is within 10 minutes ± 30 seconds
                booking_datetime = datetime.combine(booking.date, booking.time)
                time_diff = (booking_datetime - datetime.now()).total_seconds()
                
                # If between 9:30 and 10:30 minutes (600 ± 30 seconds)
                if 570 <= time_diff <= 630:
                    notify_employee(booking.employee, booking)

if __name__ == '__main__':
    print("🔔 بدء خدمة إشعارات الحجوزات PWA...")
    print("سيتم إرسال إشعار push notification للموظفين قبل 10 دقائق من بدء الحجز")
    print("-" * 50)
    
    # TODO: Install pywebpush first: pip install pywebpush
    # TODO: Generate VAPID keys
    # TODO: Add push_subscription field to User model
    # TODO: Add subscribe endpoint to save employee's push subscription
    
    while True:
        check_upcoming_bookings()
        # Check every 30 seconds
        time.sleep(30)
