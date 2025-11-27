from flask import render_template, redirect, url_for, flash, request, jsonify
import json
from flask_login import login_required, current_user
from app import db
from app.employee import bp
from app.models import Booking, User, Subscription
from datetime import datetime, date
from app.notifications import send_push_notification

@bp.before_request
def before_request():
    if not current_user.is_authenticated or current_user.role != 'employee':
        return redirect(url_for('auth.login'))

@bp.route('/')
def index():
    # Get next upcoming booking
    next_booking = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status.in_(['assigned', 'en_route', 'arrived', 'in_progress'])
    ).order_by(Booking.date, Booking.time).first()
    
    # Quick stats
    active_bookings_count = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status.in_(['assigned', 'en_route', 'arrived', 'in_progress'])
    ).count()
    
    active_subscriptions_count = Subscription.query.filter_by(
        employee_id=current_user.id,
        status='active'
    ).count()
    
    completed_today = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status == 'completed',
        Booking.date == date.today()
    ).count()
    
    return render_template('employee/index.html', 
                         booking=next_booking,
                         active_bookings_count=active_bookings_count,
                         active_subscriptions_count=active_subscriptions_count,
                         completed_today=completed_today)

@bp.route('/bookings/active')
def active_bookings():
    """Show all active bookings assigned to this employee"""
    bookings = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status.in_(['assigned', 'en_route', 'arrived', 'in_progress'])
    ).order_by(Booking.date, Booking.time).all()
    
    return render_template('employee/active_bookings.html', bookings=bookings)

@bp.route('/booking/<int:id>/status/<status>')
def update_status(id, status):
    """Update booking status"""
    booking = Booking.query.get_or_404(id)
    if booking.employee_id != current_user.id:
        flash('غير مصرح لك بتعديل هذا الحجز')
        return redirect(url_for('employee.index'))
    
    if status in ['en_route', 'arrived', 'in_progress', 'completed']:
        booking.status = status
        if status == 'completed':
            # Add loyalty point
            current_points = (booking.customer.points or 0) + 1
            if current_points >= 10:
                booking.customer.points = 0
                booking.customer.free_washes = (booking.customer.free_washes or 0) + 1
                flash('تم إكمال الخدمة. وصل العميل لـ 10 نقاط وحصل على غسلة مجانية! 🎉', 'success')
            else:
                booking.customer.points = current_points
                flash('تم إكمال الخدمة وإضافة نقطة ولاء للعميل', 'success')
            
            # Deduct products from stock
            for booking_product in booking.products:
                product = booking_product.product
                if product.stock_quantity is not None:
                    product.stock_quantity -= booking_product.quantity
                    if product.stock_quantity < 0:
                        product.stock_quantity = 0  # Prevent negative stock
        else:
            # Define status messages in Arabic
            status_messages = {
                'en_route': {
                    'title': 'الموظف في الطريق 🚗',
                    'body': f'موظفنا في الطريق إليك! سيصل قريباً لحجزك #{booking.id}'
                },
                'arrived': {
                    'title': 'وصل الموظف ✅',
                    'body': f'وصل موظفنا إلى موقعك للحجز #{booking.id}'
                },
                'in_progress': {
                    'title': 'جاري العمل 🧼',
                    'body': f'بدأ موظفنا بتقديم خدمة {booking.service.name_ar} للحجز #{booking.id}'
                }
            }
            
            flash(f'تم تحديث الحالة بنجاح', 'success')
            
            # Send notification to customer with Arabic message
            if status in status_messages:
                print(f"🔔 Attempting to send {status} notification to customer {booking.customer.username}")
                if not booking.customer.push_subscriptions:
                    print(f"⚠️ Customer {booking.customer.username} has NO push subscriptions!")
                
                notification_data = {
                    "title": status_messages[status]['title'],
                    "body": status_messages[status]['body'],
                    "icon": "/static/images/logo.png",
                    "badge": "/static/images/logo.png",
                    "url": "/customer/bookings",
                    "data": {
                        "booking_id": booking.id,
                        "status": status
                    }
                }
                success = send_push_notification(booking.customer, notification_data)
                print(f"🔔 Notification sent result: {success}")
            
        db.session.commit()
    
    return redirect(request.referrer or url_for('employee.active_bookings'))

@bp.route('/subscriptions')
def subscriptions():
    """Show subscriptions assigned to this employee"""
    subscriptions = Subscription.query.filter_by(
        employee_id=current_user.id,
        status='active'
    ).order_by(Subscription.created_at.desc()).all()
    
    return render_template('employee/subscriptions.html', subscriptions=subscriptions)

@bp.route('/subscription/<int:id>/complete-wash', methods=['POST'])
def complete_wash(id):
    """Mark a wash as completed for subscription"""
    subscription = Subscription.query.get_or_404(id)
    
    if subscription.employee_id != current_user.id:
        flash('غير مصرح لك بتعديل هذا الاشتراك', 'error')
        return redirect(url_for('employee.subscriptions'))
    
    if subscription.remaining_washes > 0:
        subscription.remaining_washes -= 1
        
        # Check if subscription is exhausted
        if subscription.remaining_washes == 0:
            subscription.status = 'expired'
            flash('تم إنهاء غسلة واحدة. الاشتراك انتهى!', 'info')
        else:
            flash(f'تم إنهاء غسلة واحدة. متبقي: {subscription.remaining_washes} غسلة', 'success')
        
        db.session.commit()
    else:
        flash('لا يوجد غسلات متبقية في هذا الاشتراك', 'error')
    
    return redirect(url_for('employee.subscriptions'))

@bp.route('/history')
def history():
    """Show completed and cancelled bookings"""
    # Get filter from query params
    status_filter = request.args.get('status', 'completed')
    
    if status_filter not in ['completed', 'cancelled']:
        status_filter = 'completed'
    
    bookings = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status == status_filter
    ).order_by(Booking.date.desc(), Booking.time.desc()).limit(100).all()
    
    # Calculate stats
    total_completed = Booking.query.filter_by(
        employee_id=current_user.id,
        status='completed'
    ).count()
    
    total_cancelled = Booking.query.filter_by(
        employee_id=current_user.id,
        status='cancelled'
    ).count()
    
    return render_template('employee/history.html',
                         bookings=bookings,
                         status_filter=status_filter,
                         total_completed=total_completed,
                         total_cancelled=total_cancelled)

@bp.route('/stats')
def stats():
    """Show employee statistics"""
    # Total bookings
    total_bookings = Booking.query.filter_by(employee_id=current_user.id).count()
    
    # Completed bookings
    completed_bookings = Booking.query.filter_by(
        employee_id=current_user.id,
        status='completed'
    ).count()
    
    # Completion rate
    completion_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
    
    # Get completed bookings list for calculations
    completed_booking_list = Booking.query.filter_by(
        employee_id=current_user.id,
        status='completed'
    ).all()
    
    # Active subscriptions
    active_subscriptions = Subscription.query.filter_by(
        employee_id=current_user.id,
        status='active'
    ).count()
    
    # Pending bookings
    pending_bookings = Booking.query.filter(
        Booking.employee_id == current_user.id,
        Booking.status.in_(['assigned', 'en_route', 'arrived', 'in_progress'])
    ).count()
    
    # Total earnings (sum of completed bookings with accurate pricing)
    total_earnings = 0
    
    # Calculate product stats
    total_products_sold = 0
    total_products_revenue = 0
    total_services_revenue = 0
    
    for booking in completed_booking_list:
        # Calculate service price after discount/free wash
        service_price = booking.service.price if booking.service else 0
        discount_amount = 0
        
        # Check if free wash was used
        if booking.used_free_wash:
            service_price = 0
        # Check if discount code was applied
        elif booking.discount_code:
            if booking.discount_code.discount_type == 'percentage':
                discount_amount = service_price * (booking.discount_code.value / 100)
            else:
                discount_amount = booking.discount_code.value
        
        # Calculate final service price (including vehicle size price)
        final_service_price = service_price - discount_amount + (booking.vehicle_size_price or 0)
        total_services_revenue += final_service_price
        
        # Calculate products total
        products_total = sum([bp.product.price * bp.quantity for bp in booking.products])
        
        # Add to total earnings
        total_earnings += final_service_price + products_total
        
        # Update product stats
        for bp in booking.products:
            total_products_sold += bp.quantity
            total_products_revenue += (bp.product.price * bp.quantity)

    # Monthly data calculation remains the same...
    from sqlalchemy import func, extract
    current_year = datetime.now().year
    
    monthly_completed = db.session.query(
        extract('month', Booking.date).label('month'),
        func.count(Booking.id).label('count')
    ).filter(
        Booking.employee_id == current_user.id,
        Booking.status == 'completed',
        extract('year', Booking.date) == current_year
    ).group_by('month').all()
    
    # Convert to dict for easy template access
    monthly_data = {int(month): count for month, count in monthly_completed}
    
    return render_template('employee/stats.html',
                         total_bookings=total_bookings,
                         completed_bookings=completed_bookings,
                         completion_rate=completion_rate,
                         total_earnings=total_earnings,
                         total_services_revenue=total_services_revenue,
                         active_subscriptions=active_subscriptions,
                         pending_bookings=pending_bookings,
                         total_products_sold=total_products_sold,
                         total_products_revenue=total_products_revenue,
                         monthly_data=monthly_data,
                         current_year=current_year)

@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Save push notification subscription"""
    subscription_info = request.get_json()
    if subscription_info:
        current_user.push_subscription = json.dumps(subscription_info)
        db.session.commit()
        return jsonify({'status': 'success'}), 201
    return jsonify({'status': 'failed'}), 400
