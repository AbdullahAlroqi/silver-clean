from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.customer import bp
from app.customer.forms import VehicleForm, BookingForm
from app.models import Vehicle, Service, Booking, City, Neighborhood, VehicleSize

@bp.before_request
def before_request():
    if not current_user.is_authenticated or current_user.role != 'customer':
        return redirect(url_for('auth.login'))

@bp.route('/')
def index():
    upcoming_bookings = current_user.bookings.filter(Booking.status.in_(['pending', 'assigned', 'en_route', 'arrived', 'in_progress'])).all()
    return render_template('customer/index.html', upcoming_bookings=upcoming_bookings)

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
    vehicle = current_user.vehicles.filter_by(id=id).first_or_404()
    db.session.delete(vehicle)
    db.session.commit()
    flash('تم حذف المركبة')
    return redirect(url_for('customer.vehicles'))

# --- Booking System ---
@bp.route('/book', methods=['GET', 'POST'])
def book():
    form = BookingForm()
    # Populate choices with placeholder
    form.vehicle_id.choices = [(v.id, f"{v.brand} - {v.plate_number}") for v in current_user.vehicles.all()]
    form.service_id.choices = [(s.id, f"{s.name_ar} ({s.price} ريال)") for s in Service.query.all()]
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
            
            # Check for free wash or discount code (mutual exclusivity)
            use_free_wash = request.form.get('use_free_wash') == 'on'
            discount_code_str = request.form.get('discount_code', '').strip()
            
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
            
            employees = neighborhood.employees.filter_by(role='employee').all()
            available_employee = None
            
            for employee in employees:
                # Check if employee has schedule for this day
                day_of_week = booking_date.weekday()
                schedule = employee.schedules.filter_by(day_of_week=day_of_week, is_active=True).first()
                
                if not schedule:
                    continue
                
                # Check if booking time is within schedule
                booking_datetime = datetime.combine(booking_date, booking_time)
                end_datetime = booking_datetime + timedelta(minutes=90)
                
                if booking_time < schedule.start_time or end_datetime.time() > schedule.end_time:
                    continue
                
                # Check if employee has conflicting booking (check for time overlap)
                conflicts = Booking.query.filter(
                    Booking.employee_id == employee.id,
                    Booking.date == booking_date,
                    Booking.status.in_(['pending', 'assigned', 'en_route', 'arrived', 'in_progress'])
                ).all()
                
                has_conflict = False
                for existing_booking in conflicts:
                    # Calculate existing booking end time
                    existing_start = datetime.combine(booking_date, existing_booking.time)
                    existing_end = existing_start + timedelta(minutes=90)
                    
                    # Check for overlap: existing_start < new_end AND existing_end > new_start
                    if existing_start < end_datetime and existing_end > booking_datetime:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    available_employee = employee
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
                vehicle_size_price=0.0
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
            flash('تم الحجز بنجاح!')
            return redirect(url_for('customer.index'))

    return render_template('customer/booking_form.html', form=form)



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
    from app.models import Product
    products = Product.query.filter(Product.stock_quantity > 0).all()
    return jsonify([{
        'id': p.id,
        'name_ar': p.name_ar,
        'price': float(p.price),
        'image_url': p.image_url if p.image_url else ''
    } for p in products])


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
    
    # Fixed duration: 90 minutes per booking
    duration_minutes = 90
    
    # Find employees assigned to this neighborhood
    neighborhood = Neighborhood.query.get(neighborhood_id)
    if not neighborhood:
        return jsonify([])
    
    
    employees = neighborhood.employees.filter_by(role='employee').all()
    
    if not employees:
        return jsonify([])
    
    # Collect all available slots from all employees
    all_slots = set()
    
    # Get current time if booking for today
    now = datetime.now()
    is_today = booking_date == today
    
    for employee in employees:
        # Get employee's schedule for this day
        schedule = employee.schedules.filter_by(day_of_week=day_of_week, is_active=True).first()
        
        if not schedule:
            continue
        
        # Generate potential time slots
        current_time = datetime.combine(booking_date, schedule.start_time)
        end_time = datetime.combine(booking_date, schedule.end_time)
        
        # If booking for today, skip past times
        if is_today and current_time < now:
            # Round up to next 30-minute slot
            minutes_to_add = (30 - now.minute % 30) % 30
            current_time = now + timedelta(minutes=minutes_to_add)
            current_time = datetime.combine(booking_date, current_time.time())
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=duration_minutes)).time()
            
            # Check if this slot conflicts with existing bookings
            conflicts = Booking.query.filter(
                Booking.employee_id == employee.id,
                Booking.date == booking_date,
                Booking.status.in_(['pending', 'assigned', 'en_route', 'arrived', 'in_progress'])
            ).all()
            
            has_conflict = False
            for booking in conflicts:
                # Calculate existing booking end time (booking start + 90 minutes)
                booking_start = datetime.combine(booking_date, booking.time)
                booking_end = booking_start + timedelta(minutes=90)
                
                # Check for overlap
                new_slot_start = datetime.combine(booking_date, slot_start)
                new_slot_end = datetime.combine(booking_date, slot_end)
                
                if booking_start < new_slot_end and booking_end > new_slot_start:
                    has_conflict = True
                    break
            
            if not has_conflict:
                all_slots.add(slot_start.strftime('%H:%M'))
            
            current_time += timedelta(minutes=90)  # 90-minute intervals
    
    # Sort and return
    sorted_slots = sorted(list(all_slots))
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
        return redirect(url_for('customer.subscriptions'))
    
    return render_template('customer/subscribe_details.html', 
                         package=package, 
                         vehicles=available_vehicles,
                         cities=cities)

@bp.route('/loyalty')
def loyalty():
    return render_template('customer/loyalty.html')
