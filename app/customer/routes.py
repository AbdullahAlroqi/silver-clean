from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.customer import bp
from app.customer.forms import VehicleForm, BookingForm, EditProfileForm, ChangePasswordForm
from app.models import Vehicle, Service, Booking, City, Neighborhood, VehicleSize

def check_expired_bookings():
    """Auto-cancel all bookings (regular and subscription) that haven't been completed within 4 hours"""
    from datetime import datetime, timedelta
    from app.models import Subscription
    from app.utils.timezone import get_saudi_time
    
    # Find ALL bookings that are still active (assigned, en_route, arrived, in_progress)
    # and have passed their scheduled time by more than 4 hours
    expired_bookings = Booking.query.filter(
        Booking.status.in_(['assigned', 'en_route', 'arrived', 'in_progress']),
    ).all()
    
    now = get_saudi_time()
    for booking in expired_bookings:
        # Calculate booking datetime
        booking_datetime = datetime.combine(booking.date, booking.time)
        
        # Check if 4 hours have passed since the booking time
        if now.replace(tzinfo=None) > booking_datetime + timedelta(hours=4):
            # Cancel the booking
            booking.status = 'cancelled'
            
            # If it's a subscription booking, restore the wash
            if booking.subscription_id and booking.subscription:
                booking.subscription.remaining_washes += 1
                # Reactivate subscription if it was expired due to no washes
                if booking.subscription.status == 'expired' and booking.subscription.remaining_washes > 0:
                    booking.subscription.status = 'active'
            
            db.session.commit()
            print(f"Auto-cancelled expired booking #{booking.id}")

@bp.before_request
def before_request():
    if not current_user.is_authenticated or current_user.role != 'customer':
        return redirect(url_for('auth.login'))
    
    # Check for expired bookings (regular and subscription)
    try:
        check_expired_bookings()
    except Exception as e:
        print(f"Error checking expired bookings: {e}")

@bp.route('/')
def index():
    from app.models import Announcement, SubscriptionPackage, SiteSettings
    
    upcoming_bookings = current_user.bookings.filter(~Booking.status.in_(['completed', 'cancelled'])).all()
    
    # Check for unrated completed bookings
    unrated_booking = Booking.query.filter(
        Booking.customer_id == current_user.id, 
        Booking.status == 'completed', 
        (Booking.rating == None) | (Booking.rating == 0)
    ).order_by(Booking.date.desc(), Booking.time.desc()).first()
    
    # Get active announcements for carousel
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.order.asc()).all()
    
    # Get active subscription packages
    packages = SubscriptionPackage.query.filter_by(is_active=True).limit(3).all()
    
    # Get services for service selection
    services = Service.query.all()
    
    # Get loyalty settings
    site_settings = SiteSettings.get_settings()
    loyalty_threshold = site_settings.loyalty_points_threshold or 10
    
    return render_template('customer/index.html', 
                         upcoming_bookings=upcoming_bookings,
                         unrated_booking=unrated_booking,
                         announcements=announcements,
                         packages=packages,
                         services=services,
                         loyalty_threshold=loyalty_threshold)

@bp.route('/bookings')
def my_bookings():
    """View all customer bookings"""
    from sqlalchemy import case
    
    # Define status priority (lower number = higher priority/shown first)
    # assigned first, cancelled last, others in middle
    status_order = case(
        (Booking.status == 'assigned', 1),
        (Booking.status == 'en_route', 2),
        (Booking.status == 'arrived', 3),
        (Booking.status == 'in_progress', 4),
        (Booking.status == 'pending', 5),
        (Booking.status == 'completed', 6),
        (Booking.status == 'cancelled', 7),
        else_=8
    )
    
    bookings = current_user.bookings.order_by(
        status_order,
        Booking.date.desc(),
        Booking.time.desc()
    ).all()
    
    return render_template('customer/my_bookings.html', bookings=bookings)

@bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking - only allowed if status is 'assigned'"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Verify booking belongs to current user
    if booking.customer_id != current_user.id:
        flash('غير مصرح لك بإلغاء هذا الحجز', 'error')
        return redirect(url_for('customer.my_bookings'))
    
    # Only allow cancellation if booking is in 'assigned' status
    if booking.status != 'assigned':
        if booking.status == 'cancelled':
            flash('هذا الحجز ملغي بالفعل', 'error')
        elif booking.status == 'completed':
            flash('لا يمكن إلغاء حجز مكتمل', 'error')
        elif booking.status in ['en_route', 'arrived', 'in_progress']:
            flash('لا يمكن إلغاء الحجز بعد بدء تنفيذه', 'error')
        elif booking.status == 'pending':
            flash('لا يمكن إلغاء الحجز في حالة الانتظار، يرجى الاتصال بالدعم', 'error')
        else:
            flash('لا يمكن إلغاء هذا الحجز', 'error')
        return redirect(url_for('customer.my_bookings'))
    
    # Cancel the booking
    booking.status = 'cancelled'
    
    # Restore wash if this is a subscription booking
    if booking.subscription_id and booking.subscription:
        booking.subscription.remaining_washes += 1
        # Reactivate subscription if it was expired due to no washes
        if booking.subscription.status == 'expired' and booking.subscription.remaining_washes > 0:
            booking.subscription.status = 'active'
    
    db.session.commit()
    
    flash('تم إلغاء الحجز بنجاح', 'success')
    return redirect(url_for('customer.my_bookings'))

# --- Vehicle Management ---
@bp.route('/vehicles')
def vehicles():
    vehicles = current_user.vehicles.all()
    return render_template('customer/vehicles.html', vehicles=vehicles)

@bp.route('/vehicles/add', methods=['GET', 'POST'])
def add_vehicle():
    form = VehicleForm()
    # Populate vehicle sizes
    form.vehicle_size.choices = [(s.id, s.name_ar) for s in VehicleSize.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        vehicle = Vehicle(
            user_id=current_user.id, 
            brand=form.brand.data, 
            plate_number=form.plate_number.data,
            vehicle_size_id=form.vehicle_size.data
        )
        db.session.add(vehicle)
        db.session.commit()
        flash('تم إضافة المركبة بنجاح')
        return redirect(url_for('customer.vehicles'))
    return render_template('customer/vehicle_form.html', form=form, title='إضافة مركبة')

@bp.route('/vehicles/delete/<int:id>')
def delete_vehicle(id):
    from app.models import Subscription, Booking
    vehicle = current_user.vehicles.filter_by(id=id).first_or_404()
    
    # Check for active subscriptions
    active_subscription = Subscription.query.filter_by(vehicle_id=vehicle.id, status='active').first()
    if active_subscription:
        flash('لا يمكن حذف المركبة لارتباطها باشتراك فعال', 'error')
        return redirect(url_for('customer.vehicles'))
        
    # Check for unfinished bookings
    unfinished_booking = Booking.query.filter(
        Booking.vehicle_id == vehicle.id, 
        ~Booking.status.in_(['completed', 'cancelled'])
    ).first()
    
    if unfinished_booking:
        flash('لا يمكن حذف المركبة لوجود حجز جاري أو قادم', 'error')
        return redirect(url_for('customer.vehicles'))
        
    db.session.delete(vehicle)
    db.session.commit()
    flash('تم حذف المركبة')
    return redirect(url_for('customer.vehicles'))

# --- Booking System ---
@bp.route('/book', methods=['GET', 'POST'])
def book():
    # Check if user has vehicles
    user_vehicles = current_user.vehicles.all()
    if not user_vehicles:
        flash('يجب إضافة مركبة قبل الحجز', 'warning')
        return redirect(url_for('customer.add_vehicle'))
    
    form = BookingForm()
    # Populate choices with placeholder
    form.vehicle_id.choices = [(v.id, f"{v.brand} - {v.plate_number}") for v in user_vehicles]
    
    # Add placeholder for service and populate choices
    services_query = Service.query.all()
    form.service_id.choices = [('', 'اختر الخدمة')] + [(s.id, f"{s.name_ar} ({s.price} ريال)") for s in services_query]
    
    # Create a dictionary for service eligibility (ID -> Boolean)
    service_eligibility = {s.id: s.includes_free_wash for s in services_query}
    # Create a dictionary for service durations (ID -> Minutes)
    service_durations = {s.id: (s.duration if s.duration else 60) for s in services_query}
    
    # Add placeholder option for city
    form.city_id.choices = [('', 'اختر المدينة')] + [(c.id, c.name_ar) for c in City.query.filter_by(is_active=True).all()]
    
    # Dynamic neighborhood loading usually requires JS/AJAX, for now we load all or handle via JS
    # Initial load
    if form.city_id.data and form.city_id.data != '':
        try:
            city_id_int = int(form.city_id.data)
            form.neighborhood_id.choices = [(n.id, n.name_ar) for n in Neighborhood.query.filter_by(city_id=city_id_int, is_active=True).all()]
        except (ValueError, TypeError):
            form.neighborhood_id.choices = []
    else:
        form.neighborhood_id.choices = []

    if request.method == 'POST':
         # Re-populate neighborhood choices to validate
        if form.city_id.data and form.city_id.data != '':
            try:
                city_id_int = int(form.city_id.data)
                form.neighborhood_id.choices = [(n.id, n.name_ar) for n in Neighborhood.query.filter_by(city_id=city_id_int, is_active=True).all()]
            except (ValueError, TypeError):
                form.neighborhood_id.choices = []

        if form.validate_on_submit():
            from datetime import datetime, timedelta
            from app.models import DiscountCode
            
            # Get booking details
            booking_date = form.date.data
            booking_time = datetime.strptime(request.form.get('time'), '%H:%M').time()
            neighborhood_id = int(request.form.get('neighborhood_id'))
            service_id = form.service_id.data
            
            # Check for free wash or discount code (mutual exclusivity)
            use_free_wash = request.form.get('use_free_wash') == 'on'
            discount_code_str = request.form.get('discount_code', '').strip()
            
            # Validate Free Wash Eligibility for the selected service
            if use_free_wash:
                selected_service = Service.query.get(service_id)
                if not selected_service or not selected_service.includes_free_wash:
                    flash('عذراً، هذه الخدمة لا تشمل الغسلة المجانية', 'error')
                    return redirect(url_for('customer.book'))

            if use_free_wash and discount_code_str:
                flash('لا يمكن استخدام غسلة مجانية وكود خصم معاً')
                return redirect(url_for('customer.book'))
            
            discount_code = None
            discount_amount = 0
            
            # Handle discount code
            if discount_code_str:
                discount_code = DiscountCode.query.filter_by(code=discount_code_str).first()
                if not discount_code or not discount_code.is_active:
                    flash('كود الخصم غير صحيح أو غير فعال')
                    return redirect(url_for('customer.book'))
                
                # Check validity period
                now = datetime.now()
                if discount_code.valid_from and now < discount_code.valid_from:
                    flash('كود الخصم لم يبدأ بعد')
                    return redirect(url_for('customer.book'))
                if discount_code.valid_until and now > discount_code.valid_until:
                    flash('كود الخصم منتهي الصلاحية')
                    return redirect(url_for('customer.book'))
                
                # Check usage limit
                if discount_code.usage_limit and discount_code.used_count >= discount_code.usage_limit:
                    flash('كود الخصم وصل للحد الأقصى من الاستخدام')
                    return redirect(url_for('customer.book'))
                
                # Check per-customer usage limit
                if discount_code.max_uses_per_customer:
                    user_usage_count = Booking.query.filter_by(
                        customer_id=current_user.id,
                        discount_code_id=discount_code.id
                    ).filter(Booking.status != 'cancelled').count()
                    
                    if user_usage_count >= discount_code.max_uses_per_customer:
                        flash('لقد تجاوزت الحد المسموح لاستخدام هذا الكود')
                        return redirect(url_for('customer.book'))
            
            # Handle free wash
            if use_free_wash:
                if current_user.free_washes <= 0:
                    flash('ليس لديك غسلات مجانية متاحة')
                    return redirect(url_for('customer.book'))
            
            # Find an available employee for this time slot
            neighborhood = Neighborhood.query.get(neighborhood_id)
            if not neighborhood:
                flash('الحي غير موجود')
                return redirect(url_for('customer.book'))
            
            # Check for existing active bookings for the same vehicle on the same day
            existing_booking = Booking.query.filter(
                Booking.customer_id == current_user.id,
                Booking.vehicle_id == form.vehicle_id.data,
                Booking.date == booking_date,
                Booking.status.notin_(['cancelled', 'completed'])
            ).first()
            
            if existing_booking:
                flash('لديك حجز آخر لنفس السيارة في نفس اليوم. الرجاء اختيار يوم آخر أو إلغاء الحجز السابق.')
                return redirect(url_for('customer.book'))
            
            employees = neighborhood.employees.filter_by(role='employee').all()
            available_employee = None
            
            for employee in employees:
                # Check if employee has any schedule for this day
                day_of_week = booking_date.weekday()
                employee_schedules = employee.schedules.filter_by(day_of_week=day_of_week, is_active=True).all()
                
                if not employee_schedules:
                    continue
                
                # Check if booking time is within ANY of the employee's shifts
                # For night shifts, we need to determine the actual booking datetime
                booking_datetime = datetime.combine(booking_date, booking_time)
                
                # Get selected service duration
                selected_service = Service.query.get(service_id)
                duration_minutes = selected_service.duration if selected_service and selected_service.duration else 60
                
                # Check if booking fits in any shift (including night shifts)
                fits_in_schedule = False
                actual_booking_datetime = booking_datetime
                actual_booking_date = booking_date
                
                for schedule in employee_schedules:
                    schedule_start = datetime.combine(booking_date, schedule.start_time)
                    schedule_end = datetime.combine(booking_date, schedule.end_time)
                    
                    # Night Shift Detection: if end_time <= start_time, shift extends to next day
                    is_night_shift = schedule.end_time <= schedule.start_time
                    if is_night_shift:
                        schedule_end += timedelta(days=1)
                    
                    # For times after midnight (00:00-05:59) in night shifts, 
                    # the actual datetime is the next day
                    test_datetime = booking_datetime
                    if is_night_shift and booking_time < schedule.start_time:
                        # This is a time after midnight, actual date is next day
                        test_datetime = booking_datetime + timedelta(days=1)
                    
                    end_datetime = test_datetime + timedelta(minutes=duration_minutes)
                    
                    if test_datetime >= schedule_start and end_datetime <= schedule_end:
                        fits_in_schedule = True
                        actual_booking_datetime = test_datetime
                        actual_booking_date = test_datetime.date()
                        break
                
                if not fits_in_schedule:
                    continue
                
                end_datetime = actual_booking_datetime + timedelta(minutes=duration_minutes)
                
                # Check if employee has conflicting booking (check for time overlap)
                # For night shifts, we need to check both the selected date and next day
                # Check for any booking that is NOT completed or cancelled
                next_day = booking_date + timedelta(days=1)
                conflicts = Booking.query.filter(
                    Booking.employee_id == employee.id,
                    Booking.date.in_([booking_date, next_day]),
                    ~Booking.status.in_(['completed', 'cancelled'])
                ).all()
                
                has_conflict = False
                for existing_booking in conflicts:
                    # Calculate existing booking end time
                    existing_start = datetime.combine(existing_booking.date, existing_booking.time)
                    # Use existing booking's service duration or default to 60
                    existing_duration = existing_booking.service.duration if existing_booking.service and existing_booking.service.duration else 60
                    existing_end = existing_start + timedelta(minutes=existing_duration)
                    
                    # Check for overlap: existing_start < new_end AND existing_end > new_start
                    if existing_start < end_datetime and existing_end > actual_booking_datetime:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    available_employee = employee
                    # Store actual booking date/time for night shift bookings
                    booking_date = actual_booking_date
                    booking_time = actual_booking_datetime.time()
                    break
            
            if not available_employee:
                flash('عذراً، لا يوجد موظفين متاحين في هذا الوقت')
                return redirect(url_for('customer.book'))
            
            # Create booking with assigned employee
            booking = Booking(
                customer_id=current_user.id,
                employee_id=available_employee.id,
                vehicle_id=form.vehicle_id.data,
                service_id=form.service_id.data,
                neighborhood_id=neighborhood_id,
                date=booking_date,
                time=booking_time,
                status='assigned',
                discount_code_id=discount_code.id if discount_code else None,
                used_free_wash=use_free_wash,
                vehicle_size_price=0.0,
                payment_method=request.form.get('payment_method', 'cash')
            )
            
            # Get vehicle size price
            vehicle = Vehicle.query.get(form.vehicle_id.data)
            if vehicle and vehicle.size:
                booking.vehicle_size_price = vehicle.size.price_adjustment
            db.session.add(booking)
            db.session.flush()  # Get booking ID before adding products
            
            # Handle product selections
            from app.models import BookingProduct, Product
            for key in request.form.keys():
                if key.startswith('product_') and request.form.get(key):
                    product_id = int(request.form.get(key))
                    quantity_key = f'quantity_{product_id}'
                    quantity = int(request.form.get(quantity_key, 1))
                    
                    booking_product = BookingProduct(
                        booking_id=booking.id,
                        product_id=product_id,
                        quantity=quantity
                    )
                    db.session.add(booking_product)
            
            # Apply free wash or discount
            if use_free_wash:
                current_user.free_washes -= 1
                flash('تم استخدام غسلة مجانية!')
            elif discount_code:
                # Increment usage count
                discount_code.used_count += 1
                flash(f'تم تطبيق كود الخصم: {discount_code.code}')
            
            db.session.commit()
            
            # Notify assigned employee
            if available_employee:
                try:
                    from app.notifications import send_push_notification
                    notification_data = {
                        "title": "حجز جديد تم تعيينه لك 🆕",
                        "body": f"تم تعيين حجز جديد #{booking.id}\nالعميل: {current_user.username}\nالخدمة: {booking.service.name_ar}\nالموعد: {booking.date} {booking.time.strftime('%H:%M')}",
                        "icon": "/static/images/logo.png",
                        "badge": "/static/images/logo.png",
                        "url": "/employee/bookings/active",
                        "data": {
                            "booking_id": booking.id
                        }
                    }
                    send_push_notification(available_employee, notification_data)
                except Exception as e:
                    print(f"Failed to send notification to employee: {e}")
            flash('تم الحجز بنجاح!')
            return redirect(url_for('customer.booking_success'))

    return render_template('customer/booking_form.html', form=form, service_eligibility=service_eligibility, service_durations=service_durations)

@bp.route('/api/vehicle/<int:vehicle_id>/size-price')
def get_vehicle_size_price(vehicle_id):
    """Get the size price for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    size_price = vehicle.size.price_adjustment if vehicle.size else 0
    return jsonify({'size_price': size_price})

@bp.route('/api/neighborhoods/<int:city_id>')
def get_neighborhoods(city_id):
    neighborhoods = Neighborhood.query.filter_by(city_id=city_id, is_active=True).all()
    return jsonify([{'id': n.id, 'name': n.name_ar} for n in neighborhoods])

@bp.route('/api/products')
def get_products():
    from app.models import Product, ProductStock, Neighborhood
    
    neighborhood_id = request.args.get('neighborhood_id')
    available_products = []
    
    if neighborhood_id:
        try:
            neighborhood_id = int(neighborhood_id)
            neighborhood = Neighborhood.query.get(neighborhood_id)
            city_id = neighborhood.city_id if neighborhood else None
            
            all_products = Product.query.all()
            
            for p in all_products:
                # Default to global stock
                current_stock = p.stock_quantity
                
                if city_id:
                    # Check city-wide stock (neighborhood_id is None)
                    city_stock = ProductStock.query.filter_by(
                        product_id=p.id, 
                        city_id=city_id, 
                        neighborhood_id=None
                    ).first()
                    
                    if city_stock:
                        current_stock = city_stock.quantity
                    
                    # Check specific neighborhood stock (overrides city/global)
                    neigh_stock = ProductStock.query.filter_by(
                        product_id=p.id, 
                        neighborhood_id=neighborhood_id
                    ).first()
                    
                    if neigh_stock:
                        current_stock = neigh_stock.quantity
                
                if current_stock > 0:
                    available_products.append(p)
        except (ValueError, AttributeError):
            # Fallback to global stock if invalid ID
            available_products = Product.query.filter(Product.stock_quantity > 0).all()
    else:
        # No neighborhood specified, show globally available products
        available_products = Product.query.filter(Product.stock_quantity > 0).all()

    return jsonify([{
        'id': p.id,
        'name_ar': p.name_ar,
        'price': float(p.price),
        'image_url': p.image_url if p.image_url else ''
    } for p in available_products])


@bp.route('/api/verify-discount', methods=['POST'])
@login_required
def verify_discount():
    """Verify discount code via AJAX"""
    try:
        from app.models import DiscountCode
        from datetime import datetime
        
        code = request.json.get('code', '').strip()
        if not code:
            return jsonify({'valid': False, 'message': 'الرجاء إدخال كود الخصم'})
        
        discount_code = DiscountCode.query.filter_by(code=code).first()
        if not discount_code or not discount_code.is_active:
            return jsonify({'valid': False, 'message': 'كود الخصم غير صحيح أو غير فعال'})
        
        # Check validity period
        now = datetime.now()
        if discount_code.valid_from and now < discount_code.valid_from:
            return jsonify({'valid': False, 'message': 'كود الخصم لم يبدأ بعد'})
        if discount_code.valid_until and now > discount_code.valid_until:
            return jsonify({'valid': False, 'message': 'كود الخصم منتهي الصلاحية'})
        
        # Check usage limit
        if discount_code.usage_limit and discount_code.used_count >= discount_code.usage_limit:
            return jsonify({'valid': False, 'message': 'كود الخصم وصل للحد الأقصى من الاستخدام'})
            
        # Check per-customer usage limit
        if discount_code.max_uses_per_customer:
            from flask_login import current_user
            from app.models import Booking
            
            if current_user.is_authenticated:
                user_usage_count = Booking.query.filter_by(
                    customer_id=current_user.id,
                    discount_code_id=discount_code.id
                ).filter(Booking.status != 'cancelled').count()
                
                if user_usage_count >= discount_code.max_uses_per_customer:
                    return jsonify({'valid': False, 'message': 'لقد تجاوزت الحد المسموح لاستخدام هذا الكود'})
        
        return jsonify({
            'valid': True,
            'message': 'كود الخصم صالح!',
            'discount_value': discount_code.value,
            'discount_type': discount_code.discount_type
        })
    except Exception as e:
        print(f"Error in verify_discount: {str(e)}")
        return jsonify({'valid': False, 'message': f'حدث خطأ: {str(e)}'})

@bp.route('/api/available-times')
def get_available_times():
    from datetime import datetime, timedelta, time as dt_time
    from app.models import User, EmployeeSchedule
    
    # Get query parameters
    date_str = request.args.get('date')
    neighborhood_id = request.args.get('neighborhood_id', type=int)
    service_id = request.args.get('service_id', type=int)
    
    if not all([date_str, neighborhood_id, service_id]):
        return jsonify([])
    
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_of_week = booking_date.weekday()  # 0=Monday, 6=Sunday
    except ValueError:
        return jsonify([])
    
    # Prevent booking dates in the past
    from datetime import date as date_class
    today = date_class.today()
    if booking_date < today:
        return jsonify([])
    
    # Dynamic duration based on service
    service = Service.query.get(service_id)
    duration_minutes = service.duration if service and service.duration else 60
    
    # 15-minute intervals for start times
    interval_minutes = 15
    
    # Find employees assigned to this neighborhood
    neighborhood = Neighborhood.query.get(neighborhood_id)
    if not neighborhood:
        return jsonify([])
    
    
    employees = neighborhood.employees.filter_by(role='employee').all()
    
    if not employees:
        return jsonify([])
    
    # Collect all available slots from all employees
    # Format: (display_time_str, actual_datetime)
    all_slots = {}
    
    # Get current time if booking for today
    now = datetime.now()
    is_today = booking_date == today
    
    for employee in employees:
        # Get ALL employee's schedules for this day (supports multiple shifts)
        employee_schedules = employee.schedules.filter_by(day_of_week=day_of_week, is_active=True).all()
        
        if not employee_schedules:
            continue
        
        # Get all existing bookings for this employee on this date AND next date (for night shifts)
        # Check for any booking that is NOT completed or cancelled (clearer and future-proof)
        next_date = booking_date + timedelta(days=1)
        conflicts = Booking.query.filter(
            Booking.employee_id == employee.id,
            Booking.date.in_([booking_date, next_date]),
            ~Booking.status.in_(['completed', 'cancelled'])
        ).all()
        
        # Process each shift
        for schedule in employee_schedules:
            # Generate potential time slots for this shift
            shift_start = datetime.combine(booking_date, schedule.start_time)
            shift_end = datetime.combine(booking_date, schedule.end_time)
            
            # Night Shift Detection: if end_time <= start_time, shift extends to next day
            is_night_shift = schedule.end_time <= schedule.start_time
            if is_night_shift:
                shift_end += timedelta(days=1)
            
            current_time = shift_start
            
            # If booking for today, skip past times
            if is_today and current_time < now:
                # Round up to next 15-minute slot
                minutes_to_add = (interval_minutes - now.minute % interval_minutes) % interval_minutes
                if minutes_to_add == 0:
                    minutes_to_add = interval_minutes
                current_time = now + timedelta(minutes=minutes_to_add)
                current_time = current_time.replace(second=0, microsecond=0)
                
                # Make sure we don't start before this shift's start time
                if current_time < shift_start:
                    current_time = shift_start
            
            # Generate slots while service can complete within shift
            while current_time + timedelta(minutes=duration_minutes) <= shift_end:
                slot_end_datetime = current_time + timedelta(minutes=duration_minutes)
                
                # Check if this slot conflicts with existing bookings
                has_conflict = False
                for booking in conflicts:
                    # Calculate existing booking time range
                    booking_start = datetime.combine(booking.date, booking.time)
                    existing_duration = booking.service.duration if booking.service and booking.service.duration else 60
                    booking_end = booking_start + timedelta(minutes=existing_duration)
                    
                    # Check for overlap: slot_start < booking_end AND slot_end > booking_start
                    if current_time < booking_end and slot_end_datetime > booking_start:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    # Additional check: if booking for today, ensure time slot hasn't passed
                    if is_today and current_time <= now:
                        current_time += timedelta(minutes=interval_minutes)
                        continue
                    
                    # Display time: show the time portion only (customer sees it as same day)
                    display_time = current_time.strftime('%H:%M')
                    
                    # Store with actual datetime for proper ordering
                    # For night shifts, times after midnight come after times before midnight
                    if display_time not in all_slots:
                        all_slots[display_time] = current_time
                
                current_time += timedelta(minutes=interval_minutes)
    
    # Sort slots: regular times (before midnight) first, then night times (after midnight)
    def sort_key(slot_str):
        hour = int(slot_str.split(':')[0])
        # Times 00:00-05:59 are considered "after midnight" and should come after 22:00-23:59
        if hour < 6:
            return (1, hour)  # Group 1 (after midnight)
        return (0, hour)  # Group 0 (regular hours)
    
    sorted_slots = sorted(all_slots.keys(), key=sort_key)
    return jsonify(sorted_slots)

# --- Subscription System ---
from app.models import SubscriptionPackage, Subscription
from datetime import datetime, timedelta


@bp.route('/subscriptions')
def subscriptions():
    my_subscriptions = current_user.subscriptions.order_by(Subscription.id.desc()).all()
    return render_template('customer/my_subscriptions.html', subscriptions=my_subscriptions)

@bp.route('/subscribe')
def subscribe_flow():
    """Show available packages"""
    # Check if user has vehicles
    user_vehicles = current_user.vehicles.all()
    if not user_vehicles:
        flash('يجب إضافة مركبة قبل الاشتراك', 'warning')
        return redirect(url_for('customer.add_vehicle'))
    
    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    
    # Get all active/pending subscriptions for this user
    active_subs = Subscription.query.filter(
        Subscription.customer_id == current_user.id,
        Subscription.status.in_(['active', 'pending'])
    ).all()
    
    # Get subscribed vehicle IDs
    subscribed_vehicle_ids = {sub.vehicle_id for sub in active_subs if sub.vehicle_id}
    
    # Get user's vehicles
    user_vehicles = current_user.vehicles.all()
    
    # Check if user can subscribe (has vehicles without subscriptions)
    can_subscribe = len(user_vehicles) > len(subscribed_vehicle_ids)
    
    # Show warning if user has all vehicles subscribed
    existing = None if can_subscribe else (active_subs[0] if active_subs else None)
    
    return render_template('customer/subscribe_packages.html', 
                         packages=packages, 
                         existing=existing,
                         can_subscribe=can_subscribe)

@bp.route('/subscribe/<int:package_id>/details', methods=['GET', 'POST'])
def subscribe_details(package_id):
    """Select vehicle and preferred time"""
    package = SubscriptionPackage.query.get_or_404(package_id)
    
    # Get all active/pending subscriptions
    active_subs = Subscription.query.filter(
        Subscription.customer_id == current_user.id,
        Subscription.status.in_(['active', 'pending'])
    ).all()
    
    # Get subscribed vehicle IDs
    subscribed_vehicle_ids = {sub.vehicle_id for sub in active_subs if sub.vehicle_id}
    
    # Get available vehicles (not subscribed)
    all_vehicles = current_user.vehicles.all()
    available_vehicles = [v for v in all_vehicles if v.id not in subscribed_vehicle_ids]
    
    if not available_vehicles:
        flash('جميع مركباتك لديها اشتراكات. يمكنك إضافة مركبة جديدة للاشتراك.')
        return redirect(url_for('customer.vehicles'))
    
    # Get cities
    cities = City.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id', type=int)
        neighborhood_id = request.form.get('neighborhood_id', type=int)
        preferred_time = request.form.get('preferred_time')
        
        if not all([vehicle_id, neighborhood_id]):
            flash('الرجاء تعبئة جميع الحقول المطلوبة')
            return redirect(url_for('customer.subscribe_details', package_id=package_id))
        
        # Check if vehicle already has subscription
        if vehicle_id in subscribed_vehicle_ids:
            flash('هذه المركبة لديها اشتراك بالفعل')
            return redirect(url_for('customer.subscribe_details', package_id=package_id))
        
        # Create subscription
        subscription = Subscription(
            customer_id=current_user.id,
            package_id=package.id,
            vehicle_id=vehicle_id,
            neighborhood_id=neighborhood_id,
            plan_type=package.name_ar,
            remaining_washes=package.wash_count,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=package.duration_days)).date(),
            status='pending'
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        flash('تم إرسال طلب الاشتراك بنجاح!')
        return redirect(url_for('customer.subscription_success'))
    
    return render_template('customer/subscribe_details.html', 
                         package=package, 
                         vehicles=available_vehicles,
                         cities=cities)

@bp.route('/subscription/<int:subscription_id>/book', methods=['GET', 'POST'])
def book_subscription_wash(subscription_id):
    """Book a wash from active subscription"""
    from datetime import datetime, timedelta
    from app.models import Subscription, Service
    
    # Get subscription and verify ownership
    subscription = Subscription.query.get_or_404(subscription_id)
    if subscription.customer_id != current_user.id:
        flash('غير مصرح لك بالوصول لهذا الاشتراك', 'error')
        return redirect(url_for('customer.subscriptions'))
    
    # Check subscription is active and has remaining washes
    if subscription.status != 'active':
        flash('الاشتراك غير فعال', 'error')
        return redirect(url_for('customer.subscriptions'))
    
    if subscription.remaining_washes <= 0:
        flash('لا توجد غسلات متبقية في هذا الاشتراك', 'error')
        return redirect(url_for('customer.subscriptions'))
    
    # Get default service (first one or a specific wash service)
    default_service = Service.query.first()
    
    if request.method == 'POST':
        booking_date_str = request.form.get('date')
        booking_time_str = request.form.get('time')
        
        if not all([booking_date_str, booking_time_str]):
            flash('الرجاء اختيار التاريخ والوقت', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            booking_time = datetime.strptime(booking_time_str, '%H:%M').time()
        except ValueError:
            flash('تنسيق التاريخ أو الوقت غير صحيح', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        # Find available employee (same logic as regular booking)
        neighborhood = subscription.neighborhood
        if not neighborhood:
            flash('الحي غير محدد في الاشتراك', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        employees = neighborhood.employees.filter_by(role='employee').all()
        available_employee = None
        
        for employee in employees:
            # Check if employee has any schedule for this day
            day_of_week = booking_date.weekday()
            employee_schedules = employee.schedules.filter_by(day_of_week=day_of_week, is_active=True).all()
            
            if not employee_schedules:
                continue
            
            # Check if booking time is within ANY of the employee's shifts
            booking_datetime = datetime.combine(booking_date, booking_time)
            
            # Check if booking fits in any shift (including night shifts)
            fits_in_schedule = False
            actual_booking_datetime = booking_datetime
            actual_booking_date = booking_date
            
            for schedule in employee_schedules:
                schedule_start = datetime.combine(booking_date, schedule.start_time)
                schedule_end = datetime.combine(booking_date, schedule.end_time)
                
                # Night Shift Detection: if end_time <= start_time, shift extends to next day
                is_night_shift = schedule.end_time <= schedule.start_time
                if is_night_shift:
                    schedule_end += timedelta(days=1)
                
                # For times after midnight in night shifts, actual datetime is next day
                test_datetime = booking_datetime
                if is_night_shift and booking_time < schedule.start_time:
                    test_datetime = booking_datetime + timedelta(days=1)
                
                end_datetime = test_datetime + timedelta(minutes=90)
                
                if test_datetime >= schedule_start and end_datetime <= schedule_end:
                    fits_in_schedule = True
                    actual_booking_datetime = test_datetime
                    actual_booking_date = test_datetime.date()
                    break
            
            if not fits_in_schedule:
                continue
            
            end_datetime = actual_booking_datetime + timedelta(minutes=90)
            
            # Check for conflicts with existing bookings (check both days for night shifts)
            next_day = booking_date + timedelta(days=1)
            conflicts = Booking.query.filter(
                Booking.employee_id == employee.id,
                Booking.date.in_([booking_date, next_day]),
                ~Booking.status.in_(['completed', 'cancelled'])
            ).all()
            
            has_conflict = False
            for existing_booking in conflicts:
                existing_start = datetime.combine(existing_booking.date, existing_booking.time)
                existing_end = existing_start + timedelta(minutes=90)
                
                if existing_start < end_datetime and existing_end > actual_booking_datetime:
                    has_conflict = True
                    break
            
            if not has_conflict:
                available_employee = employee
                # Store actual booking date/time for night shift bookings
                booking_date = actual_booking_date
                booking_time = actual_booking_datetime.time()
                break
        
        if not available_employee:
            flash('عذراً، لا يوجد موظفين متاحين في هذا الوقت', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        # Create booking linked to subscription
        booking = Booking(
            customer_id=current_user.id,
            employee_id=available_employee.id,
            vehicle_id=subscription.vehicle_id,
            service_id=default_service.id if default_service else None,
            neighborhood_id=subscription.neighborhood_id,
            date=booking_date,
            time=booking_time,
            status='assigned',
            subscription_id=subscription.id,  # Link to subscription
            used_free_wash=False,
            vehicle_size_price=0.0,
            payment_method='subscription'
        )
        
        db.session.add(booking)
        
        # Decrement remaining washes
        subscription.remaining_washes -= 1
        if subscription.remaining_washes == 0:
            subscription.status = 'expired'
        
        db.session.commit()
        
        # Notify employee
        try:
            from app.notifications import send_push_notification
            notification_data = {
                "title": "حجز جديد (اشتراك) 🆕",
                "body": f"حجز جديد #{booking.id}\nالعميل: {current_user.username}\nالموعد: {booking.date} {booking.time.strftime('%H:%M')}",
                "icon": "/static/images/logo.png",
                "badge": "/static/images/logo.png",
                "url": "/employee/bookings/active",
                "data": {"booking_id": booking.id}
            }
            send_push_notification(available_employee, notification_data)
        except Exception as e:
            print(f"Failed to send notification: {e}")
        
        flash('تم حجز الغسلة بنجاح!', 'success')
        return redirect(url_for('customer.subscriptions'))
    
    return render_template('customer/book_subscription_wash.html', subscription=subscription)

@bp.route('/loyalty')
def loyalty():
    from app.models import SiteSettings
    settings = SiteSettings.get_settings()
    return render_template('customer/loyalty.html', site_settings=settings)

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    profile_form = EditProfileForm()
    password_form = ChangePasswordForm()
    
    if 'submit_profile' in request.form and profile_form.validate_on_submit():
        current_user.username = profile_form.username.data
        current_user.email = profile_form.email.data
        current_user.phone = profile_form.phone.data
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح')
        return redirect(url_for('customer.profile'))
        
    if 'submit_password' in request.form and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('كلمة المرور الحالية غير صحيحة', 'error')
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash('تم تغيير كلمة المرور بنجاح')
            return redirect(url_for('customer.profile'))
            
    # Pre-populate profile form
    if request.method == 'GET':
        profile_form.username.data = current_user.username
        profile_form.email.data = current_user.email
        profile_form.phone.data = current_user.phone
        
    return render_template('customer/profile.html', 
                         profile_form=profile_form, 
                         password_form=password_form)

@bp.route('/booking/<int:booking_id>/rate', methods=['GET', 'POST'])
@login_required
def rate_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Security check: ensure booking belongs to current user
    if booking.customer_id != current_user.id:
        flash('لا يمكنك تقييم هذا الحجز', 'error')
        return redirect(url_for('main.index'))
        
    # Ensure booking is completed
    if booking.status != 'completed':
        flash('لا يمكن تقييم الحجز قبل اكتماله', 'warning')
        return redirect(url_for('customer.my_bookings'))
        
    # Check if already rated
    if booking.rating:
        flash('لقد قمت بتقييم هذا الحجز مسبقاً', 'info')
        return redirect(url_for('customer.my_bookings'))

    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if rating:
            booking.rating = int(rating)
            booking.rating_comment = comment
            booking.rating_date = datetime.utcnow()
            db.session.commit()
            flash('شكراً لك! تم استلام تقييمك بنجاح', 'success')
            return redirect(url_for('customer.my_bookings'))
        else:
            flash('الرجاء اختيار التقييم', 'error')
            
    return render_template('customer/rate_booking.html', booking=booking)


# ===== Success Pages =====

@bp.route('/booking/success')
def booking_success():
    """Booking success confirmation page"""
    return render_template('customer/booking_success.html')

@bp.route('/subscription/success')
def subscription_success():
    """Subscription success confirmation page"""
    return render_template('customer/subscription_success.html')


# ===== Gift Feature Routes =====

@bp.route('/gift')
def gift():
    """Main gift page with two options"""
    return render_template('customer/gift.html')


@bp.route('/gift/wash', methods=['GET', 'POST'])
def gift_wash():
    """Gift a single wash"""
    from app.models import Service, Product, GiftOrder, GiftOrderProduct, City
    
    services = Service.query.all()
    products = Product.query.all()  # Get all products
    cities = City.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        recipient_name = request.form.get('recipient_name')
        recipient_phone = request.form.get('recipient_phone')
        city_id = request.form.get('city_id')
        neighborhood_id = request.form.get('neighborhood_id')
        
        # Validate phone (9 digits)
        if not recipient_phone or len(recipient_phone) != 9 or not recipient_phone.isdigit():
            flash('الرجاء إدخال رقم جوال صحيح (9 أرقام بدون صفر)', 'error')
            return render_template('customer/gift_wash.html', services=services, products=products, cities=cities)
        
        # Format phone number with Saudi country code
        formatted_phone = '+966' + recipient_phone
        
        # Create gift order with location
        gift_order = GiftOrder(
            sender_id=current_user.id,
            recipient_name=recipient_name,
            recipient_phone=formatted_phone,
            city_id=int(city_id) if city_id else None,
            neighborhood_id=int(neighborhood_id) if neighborhood_id else None,
            gift_type='wash',
            service_id=service_id,
            status='pending'
        )
        db.session.add(gift_order)
        db.session.flush()  # Get ID for products
        
        # Add selected products
        for product in products:
            qty = request.form.get(f'product_{product.id}', 0, type=int)
            if qty > 0:
                gift_product = GiftOrderProduct(
                    gift_order_id=gift_order.id,
                    product_id=product.id,
                    quantity=qty
                )
                db.session.add(gift_product)
        
        db.session.commit()
        return redirect(url_for('customer.gift_success'))
    
    return render_template('customer/gift_wash.html', services=services, products=products, cities=cities)


@bp.route('/gift/subscription', methods=['GET', 'POST'])
def gift_subscription():
    """Gift a subscription package"""
    from app.models import SubscriptionPackage, GiftOrder
    
    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        package_id = request.form.get('package_id')
        recipient_name = request.form.get('recipient_name')
        recipient_phone = request.form.get('recipient_phone')
        
        # Validate phone (9 digits)
        if not recipient_phone or len(recipient_phone) != 9 or not recipient_phone.isdigit():
            flash('الرجاء إدخال رقم جوال صحيح (9 أرقام بدون صفر)', 'error')
            return render_template('customer/gift_subscription.html', packages=packages)
        
        # Format phone number with Saudi country code
        formatted_phone = '+966' + recipient_phone
        
        # Create gift order
        gift_order = GiftOrder(
            sender_id=current_user.id,
            recipient_name=recipient_name,
            recipient_phone=formatted_phone,
            gift_type='subscription',
            package_id=package_id,
            status='pending'
        )
        db.session.add(gift_order)
        db.session.commit()
        
        return redirect(url_for('customer.gift_success'))
    
    return render_template('customer/gift_subscription.html', packages=packages)


@bp.route('/gift/success')
def gift_success():
    """Gift order success page"""
    return render_template('customer/gift_success.html')


@bp.route('/more')
def more():
    """More options page - accessed from bottom navigation"""
    return render_template('customer/more.html')
