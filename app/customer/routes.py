from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.customer import bp
from app.customer.forms import VehicleForm, BookingForm, EditProfileForm, ChangePasswordForm
from app.models import (
    Vehicle, Service, Booking, City, Neighborhood, VehicleSize, SiteSettings, 
    BookingItem, DiscountCode, Season, CityServicePrice, 
    CityProductPrice, CityPackagePrice
)

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
            # print(f"Auto-cancelled expired booking #{booking.id}")

@bp.before_request
def before_request():
    if not current_user.is_authenticated or current_user.role != 'customer':
        return redirect(url_for('auth.login'))
    
    # Check for expired bookings (regular and subscription)
    try:
        check_expired_bookings()
    except Exception as e:
        # print(f"Error checking expired bookings: {e}")
        pass

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
    services = Service.query.filter_by(is_active=True).all()
    
    # Get loyalty settings
    site_settings = SiteSettings.get_settings()
    loyalty_threshold = site_settings.loyalty_points_threshold or 10
    
    # Referral system data
    from app.models import ReferralRecord
    referral_target = site_settings.referral_target_count or 10
    referral_records = ReferralRecord.query.filter_by(referrer_id=current_user.id).order_by(ReferralRecord.created_at.desc()).all()
    referral_completed = sum(1 for r in referral_records if r.first_wash_completed)
    current_cycle_completed = referral_completed % referral_target
    
    # Auto-generate referral code if user doesn't have one
    if not current_user.referral_code:
        from app.models import User as UserModel
        current_user.referral_code = UserModel.generate_referral_code()
        db.session.commit()
    
    return render_template('customer/index.html', 
                         upcoming_bookings=upcoming_bookings,
                         unrated_booking=unrated_booking,
                         announcements=announcements,
                         packages=packages,
                         services=services,
                         loyalty_threshold=loyalty_threshold,
                         referral_records=referral_records,
                         referral_completed=referral_completed,
                         current_cycle_completed=current_cycle_completed,
                         referral_target=referral_target)

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

@bp.route('/referrals')
def referrals():
    """View customer's referral dashboard"""
    from app.models import ReferralRecord, SiteSettings
    
    site_settings = SiteSettings.get_settings()
    referral_target = site_settings.referral_target_count or 10
    referral_records = ReferralRecord.query.filter_by(referrer_id=current_user.id).order_by(ReferralRecord.created_at.desc()).all()
    referral_completed = sum(1 for r in referral_records if r.first_wash_completed)
    current_cycle_completed = referral_completed % referral_target
    
    # Auto-generate referral code if user doesn't have one
    if not current_user.referral_code:
        from app.models import User as UserModel
        current_user.referral_code = UserModel.generate_referral_code()
        db.session.commit()
        
    return render_template('customer/referrals.html',
                         referral_records=referral_records,
                         referral_completed=referral_completed,
                         current_cycle_completed=current_cycle_completed,
                         referral_target=referral_target)

@bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking - only allowed if status is 'assigned'"""
    from app.utils.timezone import get_saudi_time
    
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
    
    # Get cancellation reason from form - required
    cancellation_reason = request.form.get('cancellation_reason', '').strip()
    if not cancellation_reason:
        flash('يجب إدخال سبب الإلغاء', 'error')
        return redirect(url_for('customer.my_bookings'))
    
    # Cancel the booking with reason and timestamp
    booking.status = 'cancelled'
    booking.cancellation_reason = cancellation_reason
    booking.cancelled_at = get_saudi_time().replace(tzinfo=None)
    
    # Restore wash if this is a subscription booking
    if booking.subscription_id and booking.subscription:
        booking.subscription.remaining_washes += 1
        # Reactivate subscription if it was expired due to no washes
        if booking.subscription.status == 'expired' and booking.subscription.remaining_washes > 0:
            booking.subscription.status = 'active'
    
    db.session.commit()
    
    flash('تم إلغاء الحجز بنجاح', 'success')
    return redirect(url_for('customer.my_bookings'))

@bp.route('/api/neighborhood/<int:id>/boundary')
def get_neighborhood_boundary(id):
    """API Endpoint to fetch a neighborhood's boundary for the customer map picker."""
    neighborhood = Neighborhood.query.get_or_404(id)
    if neighborhood.boundary_coords:
        import json
        try:
            boundary = json.loads(neighborhood.boundary_coords)
            return jsonify({'boundary': boundary})
        except json.JSONDecodeError:
            pass
    return jsonify({'boundary': None})

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

@bp.route('/vehicles/delete/<int:id>', methods=['POST'])
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
    services_query = Service.query.filter_by(is_active=True).all()
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
            
            location_lat = request.form.get('location_lat')
            location_lng = request.form.get('location_lng')
            if not location_lat or not location_lng:
                flash('الرجاء تحديد موقعك الدقيق على الخريطة للوصول إليك', 'error')
                return redirect(url_for('customer.book'))

            # Get booking details
            booking_date = form.date.data
            
            # Check for active season
            active_season = Season.query.filter(
                Season.is_active == True,
                Season.start_date <= booking_date,
                Season.end_date >= booking_date
            ).first()
            
            # Backend Validation for Booking Days Limit
            settings = SiteSettings.get_settings()
            limit = settings.booking_days_limit if settings.booking_days_limit is not None else 7
            if limit == 0:
                flash('الحجز متوقف حالياً للكشف والصيانة', 'error')
                return redirect(url_for('customer.index'))
            
            from app.utils.timezone import get_saudi_date  
            today = get_saudi_date()
            if booking_date > today + timedelta(days=limit):
                flash(f'عذراً، الحجز متاح فقط لمدة {limit} أيام قادمة', 'error')
                return redirect(url_for('customer.book'))
                
            booking_time_str = request.form.get('time')
            if not booking_time_str:
                flash('الرجاء اختيار الوقت المتاح', 'error')
                return redirect(url_for('customer.book'))
                
            booking_time = datetime.strptime(booking_time_str, '%H:%M').time()
            neighborhood_id = int(request.form.get('neighborhood_id'))
            
            # Multi-vehicle support
            vehicle_ids = request.form.getlist('vehicle_ids[]')
            service_ids = request.form.getlist('service_ids[]')
            
            # Fallback for old forms or direct access
            if not vehicle_ids and form.vehicle_id.data:
                vehicle_ids = [str(form.vehicle_id.data)]
            if not service_ids and form.service_id.data:
                service_ids = [str(form.service_id.data)]
                
            if not vehicle_ids or not service_ids or len(vehicle_ids) != len(service_ids):
                flash('يجب اختيار مركبة وخدمة صحيحة', 'error')
                return redirect(url_for('customer.book'))

            # Validate all vehicles and services
            order_items = []
            total_duration_minutes = 0
            
            for v_id, s_id in zip(vehicle_ids, service_ids):
                v_id = int(v_id)
                s_id = int(s_id)
                vehicle = Vehicle.query.get(v_id)
                service = Service.query.get(s_id)
                
                if not vehicle or vehicle.user_id != current_user.id:
                    flash('واحدة من المركبات غير صالحة')
                    return redirect(url_for('customer.book'))
                if not service:
                    flash('واحدة من الخدمات غير صالحة')
                    return redirect(url_for('customer.book'))
                
                # Check for existing active bookings for the same vehicle on the same day/time
                existing_v_booking = Booking.query.filter(
                    Booking.customer_id == current_user.id,
                    Booking.vehicle_id == v_id,
                    Booking.date == booking_date,
                    Booking.time == booking_time,
                    Booking.status.notin_(['cancelled', 'completed'])
                ).first()
                if existing_v_booking:
                    flash(f'المركبة {vehicle.brand} ({vehicle.plate_number}) لديها حجز آخر في نفس هذا الوقت')
                    return redirect(url_for('customer.book'))

                total_duration_minutes += (service.duration if service.duration else 60)
                order_items.append({'vehicle': vehicle, 'service': service})
            
            # Check for free wash or discount code (mutual exclusivity)
            use_free_wash = request.form.get('use_free_wash') == 'on'
            discount_code_str = request.form.get('discount_code', '').strip()
            
            # Validate Free Wash Eligibility (check the first service in multi-vehicle)
            if use_free_wash:
                first_service = order_items[0]['service']
                if not first_service.includes_free_wash:
                    flash('عذراً، الخدمة الأولى المختارة لا تشمل الغسلة المجانية', 'error')
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
                from app.utils.timezone import get_saudi_time
                now = get_saudi_time().replace(tzinfo=None)
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
                    
                # Check for active season (already defined above)
                if active_season and not active_season.allow_free_washes:
                    flash('عذراً، لا يمكن استخدام الغسلات المجانية خلال هذا الوقت')
                    return redirect(url_for('customer.book'))
            
            # Find the neighborhood and validate boundaries
            neighborhood = Neighborhood.query.get(neighborhood_id)
            if not neighborhood:
                flash('الحي غير موجود')
                return redirect(url_for('customer.book'))
                
            try:
                lat = float(location_lat)
                lng = float(location_lng)
                if not neighborhood.contains_point(lat, lng):
                    flash('عذراً، الموقع المحدد يقع خارج نطاق الحي المختار. يرجى تعديل الموقع للطلب.', 'error')
                    return redirect(url_for('customer.book'))
            except (ValueError, TypeError):
                flash('إحداثيات الموقع غير صالحة', 'error')
                return redirect(url_for('customer.book'))
            
            # (Vehicle conflict check moved inside loop above)
            
            # Sticky Employee Logic: Priority to employee already assigned to this customer today
            employees = neighborhood.employees.filter_by(role='employee').all()
            
            customer_active_booking = Booking.query.filter(
                Booking.customer_id == current_user.id,
                Booking.date == booking_date,
                Booking.status.notin_(['cancelled', 'completed']),
                Booking.employee_id.isnot(None)
            ).first()
            
            if customer_active_booking:
                sticky_id = customer_active_booking.employee_id
                # Reorder employees to put the sticky employee first
                employees.sort(key=lambda x: x.id != sticky_id)
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
                
                # Get total duration for all services in the order
                duration_minutes = total_duration_minutes
                
                fits_in_schedule = False
                available_employee = None
                actual_booking_datetime = booking_datetime
                actual_booking_date = booking_date
                
                # --- Advanced Rules: Strict Single-Active-Booking Rule & Same-Employee Enforcement ---
                preferred_employee_id = None
                for v_id in vehicle_ids:
                    # 1. Check for ANY active booking (not completed/cancelled) today
                    active_prev = BookingItem.query.join(Booking).filter(
                        BookingItem.vehicle_id == v_id,
                        Booking.date == booking_date,
                        Booking.status.notin_(['cancelled', 'completed'])
                    ).first()
                    if active_prev:
                        flash(f'المركبة {active_prev.vehicle.brand} ({active_prev.vehicle.plate_number}) لديها حجز نشط حالياً هذا اليوم رقم ({active_prev.booking_id}). لا يمكن إجراء حجز آخر قبل إتمام الحجز الحالي أو إلغائه.')
                        return redirect(url_for('customer.book'))

                    # 2. Find any non-cancelled booking today to pick the preferred employee
                    prev_item = BookingItem.query.join(Booking).filter(
                        BookingItem.vehicle_id == v_id,
                        Booking.date == booking_date,
                        Booking.status.notin_(['cancelled'])
                    ).first()
                    if prev_item and prev_item.booking.employee_id:
                        preferred_employee_id = prev_item.booking.employee_id
                
                search_employees = employees
                if preferred_employee_id:
                    search_employees = [e for e in employees if e.id == preferred_employee_id]
                    if not search_employees:
                        flash('الموظف المسؤول عن هذه المركبة اليوم غير متاح في هذا الوقت', 'error')
                        return redirect(url_for('customer.book'))

                for employee in search_employees:
                    # Get ALL employee's schedules for this day
                    employee_schedules = employee.schedules.filter_by(day_of_week=actual_booking_datetime.weekday(), is_active=True).all()
                    
                    emp_fits_in_schedule = False
                    for schedule in employee_schedules:
                        schedule_start = datetime.combine(booking_date, schedule.start_time)
                        schedule_end = datetime.combine(booking_date, schedule.end_time)
                        
                        is_night_shift = schedule.end_time <= schedule.start_time
                        if is_night_shift:
                            schedule_end += timedelta(days=1)
                        
                        test_datetime = booking_datetime
                        if is_night_shift and booking_time < schedule.start_time:
                            test_datetime = booking_datetime + timedelta(days=1)
                        
                        end_datetime = test_datetime + timedelta(minutes=duration_minutes)
                        
                        if test_datetime >= schedule_start and end_datetime <= schedule_end:
                            emp_fits_in_schedule = True
                            actual_booking_datetime = test_datetime
                            actual_booking_date = test_datetime.date()
                            break
                    
                    if not emp_fits_in_schedule:
                        continue
                    
                    # Check if employee has conflicting booking (check for time overlap)
                    next_day = booking_date + timedelta(days=1)
                    conflicts = Booking.query.filter(
                        Booking.employee_id == employee.id,
                        Booking.date.in_([booking_date, next_day]),
                        ~Booking.status.in_(['completed', 'cancelled'])
                    ).all()
                    
                    has_conflict = False
                    for existing_booking in conflicts:
                        existing_start = datetime.combine(existing_booking.date, existing_booking.time)
                        existing_duration = existing_booking.total_duration
                        existing_end = existing_start + timedelta(minutes=existing_duration)
                        
                        # Use actual_booking_datetime (which identifies night shifts correctly)
                        new_booking_start = actual_booking_datetime
                        new_booking_end = actual_booking_datetime + timedelta(minutes=total_duration_minutes)
                        
                        if existing_start < new_booking_end and existing_end > new_booking_start:
                            has_conflict = True
                            break
                    
                    if not has_conflict:
                        available_employee = employee
                        fits_in_schedule = True
                        break
                
                if not available_employee:
                    continue
                
                # Store actual booking date/time if it were modified by night shifts
                booking_date = actual_booking_date
                booking_time = actual_booking_datetime.time()
                break
            
            if not available_employee:
                flash('عذراً، لا يوجد موظفين متاحين في هذا الوقت')
                return redirect(url_for('customer.book'))
            
            # Create primary booking record
            first_item = order_items[0]
            booking = Booking(
                customer_id=current_user.id,
                employee_id=available_employee.id,
                vehicle_id=first_item['vehicle'].id,
                service_id=first_item['service'].id,
                neighborhood_id=neighborhood_id,
                location_lat=float(location_lat),
                location_lng=float(location_lng),
                date=booking_date,
                time=booking_time,
                status='assigned',
                is_multi_vehicle=len(order_items) > 1,
                discount_code_id=discount_code.id if discount_code else None,
                used_free_wash=use_free_wash,
                vehicle_size_price=0.0,
                payment_method=request.form.get('payment_method', 'cash'),
                created_at=datetime.utcnow()
            )
            
            db.session.add(booking)
            db.session.flush()  # Get booking ID
            
            # --- Per-Item Pricing and BookingItem Creation ---
            total_items_price = 0
            
            for idx, item in enumerate(order_items):
                v = item['vehicle']
                s = item['service']
                
                # Pricing Logic per item
                item_service_price = s.price # Default
                size_adj = 0.0
                
                # 1. City & Size Specific Price
                city_size_price = CityServicePrice.query.filter_by(
                    city_id=neighborhood.city_id, 
                    service_id=s.id, 
                    vehicle_size_id=v.vehicle_size_id
                ).first()
                
                if city_size_price:
                    item_service_price = city_size_price.price
                    size_adj = 0.0 # City-size price is the full price
                else:
                    # Fallback to base price + size adjustment if no specific override
                    # Note: You might want to filter services in the UI to only show those with city_size_price
                    item_service_price = s.price
                    if v.size:
                        size_adj = v.size.price_adjustment
                
                # 3. Seasonal Override
                if active_season:
                    seasonal_sp = active_season.service_prices.filter_by(service_id=s.id).first()
                    if seasonal_sp:
                        item_service_price = seasonal_sp.price
                
                # Free Wash logic: Apply to first item
                final_item_price = item_service_price + size_adj
                if idx == 0 and use_free_wash:
                    final_item_price = 0.0
                
                total_items_price += final_item_price
                
                b_item = BookingItem(
                    booking_id=booking.id,
                    vehicle_id=v.id,
                    service_id=s.id,
                    service_price=item_service_price,
                    size_price_adjustment=size_adj,
                    total_item_price=final_item_price
                )
                db.session.add(b_item)
                
                # For compatibility/legacy, set primary booking fields from first item
                if idx == 0:
                    booking.custom_service_price = item_service_price
                    booking.vehicle_size_price = size_adj

            booking.total_price = total_items_price
            
            # Handle product selections
            from app.models import BookingProduct, Product
            total_products_price = 0
            for key in request.form.keys():
                if key.startswith('product_') and request.form.get(key):
                    product_id = int(request.form.get(key))
                    quantity_key = f'quantity_{product_id}'
                    quantity = int(request.form.get(quantity_key, 1))
                    
                    product = Product.query.get(product_id)
                    if not product:
                        continue
                        
                    # Determine product unit price
                    unit_price = product.price
                    
                    # 1. Check City Product Price
                    city_product_price = CityProductPrice.query.filter_by(
                        city_id=neighborhood.city_id,
                        product_id=product.id
                    ).first()
                    
                    if city_product_price:
                        unit_price = city_product_price.price
                        
                    # 2. Apply seasonal product price if applicable
                    if active_season:
                        spp = active_season.product_prices.filter_by(product_id=product.id).first()
                        if spp:
                            unit_price = spp.price
                    
                    total_products_price += ((unit_price or 0) * (quantity or 1))
                    booking_product = BookingProduct(
                        booking_id=booking.id,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    db.session.add(booking_product)
            
            # Apply discounts on top of the calculated totals
            if discount_code:
                discount_value = 0
                if discount_code.discount_type == 'percentage':
                    # Apply percentage to the sum of services only? Usually standard.
                    discount_value = ((total_items_price or 0) * (discount_code.value or 0)) / 100
                else:
                    discount_value = discount_code.value
                
                total_order = (total_items_price + total_products_price) - discount_value
                booking.total_price = max(0, total_order)
            else:
                booking.total_price = total_items_price + total_products_price
            
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
                    # print(f"Failed to send notification to employee: {e}")
                    pass
            flash('تم الحجز بنجاح!')
            return redirect(url_for('customer.booking_success'))

    settings = SiteSettings.get_settings()
    return render_template('customer/booking_form.html', form=form, service_eligibility=service_eligibility, service_durations=service_durations, site_settings=settings)

@bp.route('/api/vehicle/<int:vehicle_id>/size-price')
def get_vehicle_size_price(vehicle_id):
    """Get the size price for a vehicle"""
    vehicle = current_user.vehicles.filter_by(id=vehicle_id).first_or_404()
    size_price = vehicle.size.price_adjustment if vehicle.size else 0
    return jsonify({'size_price': size_price})

@bp.route('/api/neighborhoods/<int:city_id>')
def get_neighborhoods(city_id):
    neighborhoods = Neighborhood.query.filter_by(city_id=city_id, is_active=True).all()
    return jsonify([{'id': n.id, 'name': n.name_ar, 'lat': n.latitude, 'lng': n.longitude} for n in neighborhoods])

@bp.route('/api/package-price/<int:package_id>/<int:city_id>')
def get_package_price(package_id, city_id):
    from app.models import CityPackagePrice, SubscriptionPackage
    package = SubscriptionPackage.query.get_or_404(package_id)
    city_price = CityPackagePrice.query.filter_by(package_id=package.id, city_id=city_id, is_active=True).first()
    
    price = city_price.price if city_price else package.price
    return jsonify({'price': price})

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
                
                # Default price
                current_price = p.price
                
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
                        
                    # Check City Product Price
                    from app.models import CityProductPrice
                    city_price = CityProductPrice.query.filter_by(
                        product_id=p.id,
                        city_id=city_id
                    ).first()
                    
                    if city_price:
                        current_price = city_price.price
                
                if current_stock > 0:
                    available_products.append({
                        'id': p.id,
                        'name_ar': p.name_ar,
                        'price': float(current_price),
                        'image_url': p.image_url if p.image_url else ''
                    })
        except (ValueError, AttributeError):
            # Fallback to global stock if invalid ID
            for p in Product.query.filter(Product.stock_quantity > 0).all():
                available_products.append({
                    'id': p.id,
                    'name_ar': p.name_ar,
                    'price': float(p.price),
                    'image_url': p.image_url if p.image_url else ''
                })
    else:
        # No neighborhood specified, show globally available products
        for p in Product.query.filter(Product.stock_quantity > 0).all():
            available_products.append({
                'id': p.id,
                'name_ar': p.name_ar,
                'price': float(p.price),
                'image_url': p.image_url if p.image_url else ''
            })

    return jsonify(available_products)


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
        # print(f"Error in verify_discount: {str(e)}")
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
    
    # Prevent booking dates in the past - Use Saudi Date
    from app.utils.timezone import get_saudi_date
    today = get_saudi_date()
    if booking_date < today:
        return jsonify([])
        
    # Check max days limit
    booking_type = request.args.get('type', 'service')
    settings = SiteSettings.get_settings()
    
    limit = settings.booking_days_limit
    if booking_type == 'subscription':
        limit = settings.subscription_days_limit
        
    # Handle None (migration might produce NULL)
    if limit is None:
        limit = 7
        
    if limit == 0:
        return jsonify([])
        
    if booking_date > today + timedelta(days=limit): 
        return jsonify([])
    
    # Dynamic duration based on service or explicit parameter
    duration_minutes = request.args.get('duration', type=int)
    if not duration_minutes:
        service = Service.query.get(service_id)
        duration_minutes = service.duration if service and service.duration else 60
    
    # 15-minute intervals for start times
    interval_minutes = 15
    
    # Find employees assigned to this neighborhood
    neighborhood = Neighborhood.query.get(neighborhood_id)
    if not neighborhood:
        return jsonify([])
    
    
    employees = neighborhood.employees.filter_by(role='employee').all()
    
    # --- New Rules: Multi-vehicle and Same-Employee Logic ---
    vehicle_ids = request.args.getlist('vehicle_ids[]')
    
    # 1. Strict Single-Active-Booking Rule: Check for active bookings today
    if vehicle_ids:
        active_booking = BookingItem.query.join(Booking).filter(
            BookingItem.vehicle_id.in_(vehicle_ids),
            Booking.date == booking_date,
            Booking.status.notin_(['cancelled', 'completed'])
        ).first()
        if active_booking:
            # If any vehicle has an active booking today, no additional bookings allowed
            return jsonify({
                'available_times': [], 
                'error': f'عذراً، لديك سيارة لديها حجز فعال حالياً لهذا اليوم رقم ({active_booking.booking_id}). يرجى إتمامه أولاً.'
            })

    # 2. Same-Employee Assignment Rule: Find preferred employee based on ANY booking today
    preferred_employee_id = None
    if vehicle_ids:
        for v_id in vehicle_ids:
            prev_item = BookingItem.query.join(Booking).filter(
                BookingItem.vehicle_id == v_id,
                Booking.date == booking_date,
                Booking.status.notin_(['cancelled'])
            ).first()
            if prev_item and prev_item.booking.employee_id:
                preferred_employee_id = prev_item.booking.employee_id
                break
                
    # If a vehicle has a preferred employee, restrict availability to that employee only
    if preferred_employee_id:
        employees = [e for e in employees if e.id == preferred_employee_id]
    
    if not employees:
        return jsonify([])
    
    # 3. Get customer's other bookings to prevent they booking multiple overlapping slots
    customer_other_bookings = []
    if current_user.is_authenticated:
        customer_other_bookings = Booking.query.filter(
            Booking.customer_id == current_user.id,
            Booking.date == booking_date,
            Booking.status.notin_(['cancelled', 'completed'])
        ).all()

    # 4. Vehicle conflicts (kept for temporal overlap check of COMPLETED/Other bookings, though Rule #1 handles active)
    vehicle_conflicts = []
    if vehicle_ids:
        vehicle_conflicts = BookingItem.query.join(Booking).filter(
            BookingItem.vehicle_id.in_(vehicle_ids),
            Booking.date == booking_date,
            Booking.status.notin_(['cancelled'])
        ).all()
    
    # Collect all available slots from all employees
    # Format: (display_time_str, actual_datetime)
    all_slots = {}
    
    # Get current time if booking for today - Use Saudi Time
    from app.utils.timezone import get_saudi_time
    # Ensure naive datetime for comparison with shift times
    now = get_saudi_time().replace(tzinfo=None)
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
                
                # Check if this slot conflicts with existing bookings (Employee, Customer, and Vehicle)
                has_conflict = False
                
                # Check Employee Conflicts (Already in code)
                for booking in conflicts:
                    b_start = datetime.combine(booking.date, booking.time)
                    b_end = b_start + timedelta(minutes=booking.total_duration)
                    if current_time < b_end and slot_end_datetime > b_start:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    # Check Customer Conflicts (Cannot have two overlapping bookings)
                    for b in customer_other_bookings:
                        b_start = datetime.combine(b.date, b.time)
                        b_end = b_start + timedelta(minutes=b.total_duration)
                        if current_time < b_end and slot_end_datetime > b_start:
                            has_conflict = True
                            break
                            
                if not has_conflict:
                    # Check Vehicle Conflicts (Car can't be washed twice at the same time)
                    for item in vehicle_conflicts:
                        b = item.booking
                        b_start = datetime.combine(b.date, b.time)
                        b_end = b_start + timedelta(minutes=b.total_duration)
                        if current_time < b_end and slot_end_datetime > b_start:
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
@login_required
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
    
    # Get default service (first active one)
    default_service = Service.query.filter_by(is_active=True).first()
    
    if request.method == 'POST':
        booking_date_str = request.form.get('date')
        booking_time_str = request.form.get('time')
        
        if not all([booking_date_str, booking_time_str]):
            flash('الرجاء اختيار التاريخ والوقت', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
            
        city_id = request.form.get('city_id')
        neighborhood_id = request.form.get('neighborhood_id')
        location_lat = request.form.get('location_lat')
        location_lng = request.form.get('location_lng')
        
        if not all([city_id, neighborhood_id, location_lat, location_lng]):
            flash('الرجاء اختيار المدينة والحي وتحديد الموقع من الخريطة', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            booking_time = datetime.strptime(booking_time_str, '%H:%M').time()
        except ValueError:
            flash('تنسيق التاريخ أو الوقت غير صحيح', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
            
        # Backend Validation for Subscription Days Limit
        settings = SiteSettings.get_settings()
        limit = settings.subscription_days_limit if settings.subscription_days_limit is not None else 7
        if limit == 0:
            flash('حجز الاشتراكات متوقف حالياً للكشف والصيانة', 'error')
            return redirect(url_for('customer.subscriptions'))
            
        from app.utils.timezone import get_saudi_date
        today = get_saudi_date()
        if booking_date > today + timedelta(days=limit):
             flash(f'عذراً، الحجز متاح فقط لمدة {limit} أيام قادمة', 'error')
             return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        # Check for existing active booking on the same day for this subscription
        # 1. Strict Single-Active-Booking Rule: Check for ANY active booking for this vehicle today
        from app.models import BookingItem
        active_prev = BookingItem.query.join(Booking).filter(
            BookingItem.vehicle_id == subscription.vehicle_id,
            Booking.date == booking_date,
            Booking.status.notin_(['cancelled', 'completed'])
        ).first()

        if active_prev:
            flash(f'عذراً، لديك حجز فعال حالياً لهذه المركبة في نفس اليوم. يرجى إتمام الحجز الحالي أولاً.', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        # Find available employee
        from app.models import Neighborhood
        neighborhood = Neighborhood.query.get(neighborhood_id)
        if not neighborhood:
            flash('الحي المحدد غير صحيح', 'error')
            return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        
        # Boundary Validation
        try:
            lat = float(location_lat)
            lng = float(location_lng)
            if not neighborhood.contains_point(lat, lng):
                flash('عذراً، الموقع المحدد يقع خارج نطاق الحي المختار. يرجى تعديل الموقع للطلب.', 'error')
                return redirect(url_for('customer.book_subscription_wash', subscription_id=subscription_id))
        except (ValueError, TypeError):
            flash('إحداثيات الموقع غير صالحة', 'error')
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
                # Determine end time based on the service duration (default to 60 if not found)
                booking_duration = default_service.duration if (default_service and default_service.duration) else 60
                end_datetime = test_datetime + timedelta(minutes=booking_duration)
                
                if test_datetime >= schedule_start and end_datetime <= schedule_end:
                    fits_in_schedule = True
                    actual_booking_datetime = test_datetime
                    actual_booking_date = test_datetime.date()
                    break
            
            if not fits_in_schedule:
                continue
            
            # Use dynamic service duration (default to 60 if not found)
            booking_duration = default_service.duration if (default_service and default_service.duration) else 60
            end_datetime = actual_booking_datetime + timedelta(minutes=booking_duration)
            
            # Check for conflicts with existing bookings (check both days for night shifts)
            next_day = booking_date + timedelta(days=1)
            conflicts = Booking.query.filter(
                Booking.employee_id == employee.id,
                Booking.date.in_([booking_date, next_day]),
                ~Booking.status.in_(['completed', 'cancelled'])
            ).all()
            
            has_conflict = False
            for existing_booking in conflicts:
                # Use total duration of all items in existing booking
                existing_duration = existing_booking.total_duration
                # Use ACTUAL scheduled time for comparison
                existing_start = datetime.combine(existing_booking.date, existing_booking.time)
                existing_end = existing_start + timedelta(minutes=existing_duration)
                
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
            neighborhood_id=neighborhood.id,
            location_lat=float(location_lat),
            location_lng=float(location_lng),
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
    
    settings = SiteSettings.get_settings()
    from app.models import City, Booking
    cities = City.query.filter_by(is_active=True).all()
    
    # Determine default city and neighborhood
    default_city_id = None
    default_neighborhood_id = None
    
    if subscription.neighborhood:
        default_city_id = subscription.neighborhood.city_id
        default_neighborhood_id = subscription.neighborhood.id
    else:
        # Fallback to last successful booking's neighborhood
        last_booking = current_user.bookings.filter(Booking.neighborhood_id.isnot(None)).order_by(Booking.id.desc()).first()
        if last_booking and last_booking.neighborhood:
            default_city_id = last_booking.neighborhood.city_id
            default_neighborhood_id = last_booking.neighborhood.id
        elif cities:
            default_city_id = cities[0].id
            
    return render_template('customer/book_subscription_wash.html', 
                           subscription=subscription, 
                           default_service=default_service, 
                           site_settings=settings, 
                           cities=cities,
                           default_city_id=default_city_id,
                           default_neighborhood_id=default_neighborhood_id)

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

@bp.route('/api/prices')
def api_prices():
    """API endpoint to get prices for a specific date (handling seasons and cities)"""
    from app.models import Season, Service, Product, CityServicePrice, CityProductPrice
    from datetime import datetime
    
    date_str = request.args.get('date')
    city_id = request.args.get('city_id')
    
    if not date_str:
        from app.utils.timezone import get_saudi_date
        booking_date = get_saudi_date()
    else:
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
    # Find active season for this date
    # A date is within a season if it falls between start_date and end_date inclusive
    active_season = Season.query.filter(
        Season.is_active == True,
        Season.start_date <= booking_date,
        Season.end_date >= booking_date
    ).first()
    
    prices = {
        'services': {},
        'products': {}
    }
    
    # Get base prices first (fallback)
    services = Service.query.filter_by(is_active=True).all()
    products = Product.query.all()
    
    for service in services:
        current_price = service.price
        if city_id:
            city_price = CityServicePrice.query.filter_by(service_id=service.id, city_id=city_id).first()
            if city_price:
                current_price = city_price.price
        prices['services'][str(service.id)] = current_price
        
    for product in products:
        current_price = product.price
        if city_id:
            city_price = CityProductPrice.query.filter_by(product_id=product.id, city_id=city_id).first()
            if city_price:
                current_price = city_price.price
        prices['products'][str(product.id)] = current_price
        
    # Override with seasonal prices if applicable
    seasonal_applied = False
    season_name = None
    allow_free_washes = False
    
    if active_season:
        seasonal_applied = True
        season_name = active_season.name_ar
        allow_free_washes = active_season.allow_free_washes
        
        for sp in active_season.service_prices:
            prices['services'][str(sp.service_id)] = sp.price
            
        for pp in active_season.product_prices:
            prices['products'][str(pp.product_id)] = pp.price
            
    return jsonify({
        'seasonal_applied': seasonal_applied,
        'season_name': season_name,
        'allow_free_washes': allow_free_washes,
        'prices': prices
    })


# ===== Gift Feature Routes =====

@bp.route('/gift')
def gift():
    """Main gift page with two options"""
    return render_template('customer/gift.html')


@bp.route('/gift/wash', methods=['GET', 'POST'])
def gift_wash():
    """Gift a single wash"""
    from app.models import Service, Product, GiftOrder, GiftOrderProduct, City
    
    services = Service.query.filter_by(is_active=True).all()
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


@bp.route('/booking/<int:booking_id>/employee-location')
def booking_employee_location(booking_id):
    """Get employee location for a specific booking (customer tracking)"""
    from app.models import EmployeeLocation
    from datetime import datetime, timedelta
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Verify booking belongs to current user
    if booking.customer_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    # Only show tracking for en_route/arrived statuses
    if booking.status not in ['en_route', 'arrived', 'in_progress']:
        return jsonify({'status': 'not_tracking', 'message': 'التتبع غير متاح حالياً'})
    
    if not booking.employee_id:
        return jsonify({'status': 'no_employee', 'message': 'لم يتم تعيين موظف بعد'})
    
    location = EmployeeLocation.query.filter_by(employee_id=booking.employee_id).first()
    
    if not location:
        return jsonify({
            'status': 'waiting',
            'message': 'في انتظار تحديث موقع الموظف',
            'employee_name': booking.employee.username if booking.employee else ''
        })
    
    seconds_since_update = (datetime.utcnow() - location.updated_at).total_seconds()
    is_stale = seconds_since_update > 60
    
    # Customer location
    customer_lat = booking.location_lat
    customer_lng = booking.location_lng
    
    return jsonify({
        'status': 'tracking',
        'employee_name': booking.employee.username if booking.employee else '',
        'latitude': location.latitude,
        'longitude': location.longitude,
        'accuracy': location.accuracy,
        'seconds_since_update': seconds_since_update,
        'is_stale': is_stale,
        'is_tracking': location.is_tracking,
        'customer_lat': customer_lat,
        'customer_lng': customer_lng,
        'booking_status': booking.status
    })


@bp.route('/booking/<int:booking_id>/track')
def track_booking(booking_id):
    """Customer tracking page for an active booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.customer_id != current_user.id:
        flash('غير مصرح لك بالوصول لهذا الحجز', 'error')
        return redirect(url_for('customer.my_bookings'))
    
    if booking.status not in ['en_route', 'arrived', 'in_progress', 'assigned']:
        flash('التتبع غير متاح لهذا الحجز', 'error')
        return redirect(url_for('customer.my_bookings'))
    
    return render_template('customer/track_booking.html', booking=booking)

@bp.route('/api/services-for-vehicle/<int:vehicle_id>')
def get_services_for_vehicle(vehicle_id):
    from app.models import Vehicle, CityServicePrice, Season, Service
    from datetime import datetime
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    city_id = request.args.get('city_id', type=int)
    date_str = request.args.get('date')
    
    booking_date = datetime.strptime(date_str, '%Y-%m-%d').date() if (date_str and date_str != 'undefined') else datetime.utcnow().date()
    
    # 1. Get prices from unified CityServicePrice for this city and vehicle size
    if city_id:
        city_prices = CityServicePrice.query.filter_by(
            city_id=city_id, 
            vehicle_size_id=vehicle.vehicle_size_id,
            is_active=True
        ).all()
    else:
        # Fallback if no city (though flow requires it) - maybe show all services with base price?
        # But for this app, we strictly use city prices now.
        return jsonify([])

    if not city_prices:
        return jsonify([])
    
    # 2. Get active season for overrides
    active_season = Season.query.filter(
        Season.is_active == True,
        Season.start_date <= booking_date,
        Season.end_date >= booking_date
    ).first()
    
    results = []
    for cp in city_prices:
        service = cp.service
        if not service or not service.is_active:
            continue
            
        # Base price from city-size override
        final_price = cp.price
        
        # Seasonal override (highest priority)
        if active_season:
            ssp = active_season.service_prices.filter_by(service_id=service.id).first()
            if ssp:
                final_price = ssp.price
        
        results.append({
            'id': service.id,
            'name': service.name_ar,
            'description': service.description,
            'price': final_price,
            'duration': service.duration
        })
        
    return jsonify(results)
