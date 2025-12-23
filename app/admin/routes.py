from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.admin import bp
from app.admin.forms import EmployeeForm, ServiceForm, VehicleSizeForm, CityForm, NeighborhoodForm, ProductForm, SubscriptionPackageForm, SiteSettingsForm, NotificationForm, AdminUserForm
from app.models import User, Service, VehicleSize, City, Neighborhood, Booking, Product, SubscriptionPackage, Subscription, EmployeeSchedule, SiteSettings, Notification, PushSubscription, BookingProduct, DiscountCode
from sqlalchemy import func, or_, extract
from datetime import date, timedelta, time, datetime
from werkzeug.utils import secure_filename
from urllib.parse import quote
import os
from pywebpush import webpush, WebPushException
import json

@bp.before_request
def before_request():
    if not current_user.is_authenticated or current_user.role not in ['admin', 'supervisor']:
        return redirect(url_for('auth.login'))

@bp.route('/')
def index():
    # Get supervisor's neighborhood scope if applicable
    supervisor_neighborhood_ids = []
    if current_user.role == 'supervisor':
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
    
    # Count employees (filter by scope for supervisors)
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            employees_count = User.query.filter_by(role='employee').join(User.neighborhoods).filter(Neighborhood.id.in_(supervisor_neighborhood_ids)).distinct().count()
            # Fix AmbiguousForeignKeysError by specifying join condition
            customers_count = User.query.filter_by(role='customer').join(Booking, User.id == Booking.customer_id).filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids)).distinct().count()
            bookings_count = Booking.query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids)).count()
        else:
            employees_count = 0
            customers_count = 0
            bookings_count = 0
    else:
        employees_count = User.query.filter_by(role='employee').count()
        customers_count = User.query.filter_by(role='customer').count()
        bookings_count = Booking.query.count()
    
    # Calculate total revenue from completed bookings
    completed_bookings_query = Booking.query.filter_by(status='completed')
    
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            completed_bookings_query = completed_bookings_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            completed_bookings_query = completed_bookings_query.filter_by(id=-1) # Empty result
            
    completed_bookings = completed_bookings_query.all()
    total_revenue = sum(b.service.price for b in completed_bookings if b.service)
    
    # Get recent bookings
    recent_bookings_query = Booking.query.order_by(Booking.date.desc(), Booking.time.desc())
    
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            recent_bookings_query = recent_bookings_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            recent_bookings_query = recent_bookings_query.filter_by(id=-1)
            
    recent_bookings = recent_bookings_query.limit(5).all()
    
    return render_template('admin/index.html', 
                           employees_count=employees_count, 
                           customers_count=customers_count, 
                           bookings_count=bookings_count,
                           total_revenue=total_revenue,
                           recent_bookings=recent_bookings)

# --- Employee Management ---
@bp.route('/employees')
def employees():
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all')

    # Base query
    query = User.query

    if role_filter == 'employee':
        query = query.filter_by(role='employee')
    elif role_filter == 'supervisor':
        query = query.filter_by(role='supervisor')
    else:
        query = query.filter(User.role.in_(['employee', 'supervisor']))

    if search_query:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search_query}%"),
                User.phone.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%")
            )
        )

    employees = query.order_by(User.id.desc()).all()

    # Counters for tabs
    all_count = User.query.filter(User.role.in_(['employee', 'supervisor'])).count()
    employee_count = User.query.filter_by(role='employee').count()
    supervisor_count = User.query.filter_by(role='supervisor').count()

    return render_template(
        'admin/employees.html',
        employees=employees,
        role_filter=role_filter,
        all_count=all_count,
        employee_count=employee_count,
        supervisor_count=supervisor_count,
    )

@bp.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    from app.models import EmployeeSchedule
    from datetime import time
    
    form = EmployeeForm()
    
    # Populate choices
    all_neighborhoods = Neighborhood.query.join(City).all()
    all_cities = City.query.all()
    
    form.neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods]
    form.supervisor_cities.choices = [(c.id, c.name_ar) for c in all_cities]
    form.supervisor_neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods]
    
    # Restrict for supervisor (the current user, not the one being created)
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        # Filter choices to only show neighborhoods within supervisor's scope
        form.neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods if n.id in supervisor_neighborhood_ids]
    
    if form.validate_on_submit():
        # Check if phone number already exists
        existing_phone = User.query.filter_by(phone=form.phone.data).first()
        if existing_phone:
            flash('رقم الهاتف مستخدم بالفعل. الرجاء استخدام رقم هاتف آخر.', 'error')
            return render_template('admin/employee_form.html', form=form, title='إضافة موظف / مشرف')
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash('اسم المستخدم موجود بالفعل. الرجاء اختيار اسم مستخدم آخر.', 'error')
            return render_template('admin/employee_form.html', form=form, title='إضافة موظف / مشرف')
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('البريد الإلكتروني مستخدم بالفعل. الرجاء استخدام بريد آخر.', 'error')
            return render_template('admin/employee_form.html', form=form, title='إضافة موظف / مشرف')
        
        # Determine role - only admin can create supervisors
        if current_user.role == 'admin' and form.role.data:
            role = form.role.data
        else:
            role = 'employee'
        
        user = User(username=form.username.data, email=form.email.data, phone=form.phone.data, role=role)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Handle based on role
        if role == 'supervisor':
            # Assign supervisor cities
            city_ids = request.form.getlist('supervisor_cities')
            for city_id in city_ids:
                city = City.query.get(int(city_id))
                if city:
                    user.supervisor_cities.append(city)
            
            # Assign supervisor neighborhoods
            neighborhood_ids = request.form.getlist('supervisor_neighborhoods')
            for neighborhood_id in neighborhood_ids:
                neighborhood = Neighborhood.query.get(int(neighborhood_id))
                if neighborhood:
                    user.supervisor_neighborhoods.append(neighborhood)
        else:
            # Assign employee neighborhoods
            neighborhood_ids = request.form.getlist('neighborhoods')
            
            # Validate supervisor scope if current user is supervisor
            if current_user.role == 'supervisor':
                allowed_ids = set(supervisor_neighborhood_ids)
                neighborhood_ids = [nid for nid in neighborhood_ids if int(nid) in allowed_ids]
                
            for neighborhood_id in neighborhood_ids:
                neighborhood = Neighborhood.query.get(int(neighborhood_id))
                if neighborhood:
                    user.neighborhoods.append(neighborhood)
            
            # Create default schedule for employees only (Sun-Thu, 8 AM - 8 PM)
            for day in [6, 0, 1, 2, 3]:  # Sunday(6) to Thursday(3)
                schedule = EmployeeSchedule(
                    employee_id=user.id,
                    day_of_week=day,
                    start_time=time(8, 0),
                    end_time=time(20, 0),
                    is_active=True
                )
                db.session.add(schedule)
        
        db.session.commit()
        flash(f'تم إضافة {"المشرف" if role == "supervisor" else "الموظف"} بنجاح')
        return redirect(url_for('admin.employees'))
    return render_template('admin/employee_form.html', form=form, title='إضافة موظف / مشرف')

@bp.route('/employees/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    employee = User.query.get_or_404(id)
    
    # Check supervisor access (only for employees, not supervisors being edited)
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        # Check if employee belongs to any of supervisor's neighborhoods
        if employee.role == 'employee':
            employee_neighborhood_ids = [n.id for n in employee.neighborhoods]
            has_access = False
            
            for nid in employee_neighborhood_ids:
                if nid in supervisor_neighborhood_ids:
                    has_access = True
                    break
            
            if not has_access and employee_neighborhood_ids:
                flash('ليس لديك صلاحية لتعديل هذا الموظف', 'error')
                return redirect(url_for('admin.employees'))
        else:
            # Supervisors cannot edit other supervisors
            flash('ليس لديك صلاحية لتعديل المشرفين', 'error')
            return redirect(url_for('admin.employees'))

    form = EmployeeForm(obj=employee)
    
    all_neighborhoods = Neighborhood.query.join(City).all()
    all_cities = City.query.all()
    
    form.neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods]
    form.supervisor_cities.choices = [(c.id, c.name_ar) for c in all_cities]
    form.supervisor_neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods]
    
    # Restrict choices for supervisor (current user)
    if current_user.role == 'supervisor':
        form.neighborhoods.choices = [(n.id, f"{n.city.name_ar} - {n.name_ar}") for n in all_neighborhoods if n.id in supervisor_neighborhood_ids]

    if request.method == 'POST':
        # Update basic info
        employee.username = request.form.get('username')
        employee.email = request.form.get('email')
        employee.phone = request.form.get('phone')
        
        # Update role if admin is editing
        if current_user.role == 'admin' and form.role.data:
            old_role = employee.role
            new_role = form.role.data
            
            # If role changed, clear old associations
            if old_role != new_role:
                if old_role == 'employee':
                    employee.neighborhoods.clear()
                elif old_role == 'supervisor':
                    employee.supervisor_cities.clear()
                    employee.supervisor_neighborhoods.clear()
                
                employee.role = new_role
        
        # Update password if provided
        password = request.form.get('password')
        if password and password.strip():
            employee.set_password(password)
        
        # Handle based on role
        if employee.role == 'supervisor':
            # Update supervisor cities
            employee.supervisor_cities.clear()
            city_ids = request.form.getlist('supervisor_cities')
            for city_id in city_ids:
                city = City.query.get(int(city_id))
                if city:
                    employee.supervisor_cities.append(city)
            
            # Update supervisor neighborhoods
            employee.supervisor_neighborhoods.clear()
            neighborhood_ids = request.form.getlist('supervisor_neighborhoods')
            for neighborhood_id in neighborhood_ids:
                neighborhood = Neighborhood.query.get(int(neighborhood_id))
                if neighborhood:
                    employee.supervisor_neighborhoods.append(neighborhood)
        else:
            # Update employee neighborhoods
            neighborhood_ids = request.form.getlist('neighborhoods')
            
            if current_user.role == 'supervisor':
                # Get current neighborhoods outside scope (to preserve them)
                preserved_neighborhoods = [n for n in employee.neighborhoods if n.id not in supervisor_neighborhood_ids]
                
                # Filter new ids to be within scope
                new_scope_ids = [int(nid) for nid in neighborhood_ids if int(nid) in supervisor_neighborhood_ids]
                
                # Rebuild list
                employee.neighborhoods = preserved_neighborhoods
                for nid in new_scope_ids:
                    n = Neighborhood.query.get(nid)
                    if n:
                        employee.neighborhoods.append(n)
            else:
                # Admin: full replace
                employee.neighborhoods.clear()
                for neighborhood_id in neighborhood_ids:
                    neighborhood = Neighborhood.query.get(int(neighborhood_id))
                    if neighborhood and neighborhood not in employee.neighborhoods:
                        employee.neighborhoods.append(neighborhood)
        
        db.session.commit()
        flash('تم تعديل البيانات بنجاح')
        return redirect(url_for('admin.employees'))
    
    # GET request - pre-populate form
    form.username.data = employee.username
    form.email.data = employee.email
    form.phone.data = employee.phone
    
    if employee.role == 'supervisor':
        form.role.data = 'supervisor'
        form.supervisor_cities.data = [c.id for c in employee.supervisor_cities]
        form.supervisor_neighborhoods.data = [n.id for n in employee.supervisor_neighborhoods]
    else:
        form.role.data = 'employee'
        form.neighborhoods.data = [n.id for n in employee.neighborhoods]

    return render_template('admin/employee_form.html', form=form, title='تعديل موظف / مشرف', employee=employee)

@bp.route('/employees/schedule/<int:id>', methods=['GET', 'POST'])
def employee_schedule(id):
    employee = User.query.get_or_404(id)
    
    days_map = {
        'sunday': 6, 'monday': 0, 'tuesday': 1, 'wednesday': 2,
        'thursday': 3, 'friday': 4, 'saturday': 5
    }
    days_form = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    
    if request.method == 'POST':
        # Clear existing schedule
        EmployeeSchedule.query.filter_by(employee_id=id).delete()
        
        for day_name in days_form:
            enabled = request.form.get(f'{day_name}_enabled')
            if enabled:
                start_time_str = request.form.get(f'{day_name}_start', '08:00')
                end_time_str = request.form.get(f'{day_name}_end', '20:00')
                
                try:
                    start_hour, start_min = map(int, start_time_str.split(':'))
                    end_hour, end_min = map(int, end_time_str.split(':'))
                    
                    schedule = EmployeeSchedule(
                        employee_id=id,
                        day_of_week=days_map[day_name],
                        start_time=time(start_hour, start_min),
                        end_time=time(end_hour, end_min),
                        is_active=True
                    )
                    db.session.add(schedule)
                except ValueError:
                    continue
        
        db.session.commit()
        flash('تم تحديث جدول العمل بنجاح')
        return redirect(url_for('admin.employees'))

    # GET: Prepare schedule data for template
    schedules = {s.day_of_week: s for s in employee.schedules}
    return render_template('admin/employee_schedule.html', employee=employee, schedules=schedules)


@bp.route('/employees/delete/<int:id>')
def delete_employee(id):
    employee = User.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    flash('تم حذف الموظف')
    return redirect(url_for('admin.employees'))

@bp.route('/employees/<int:id>/stats')
def employee_stats(id):
    employee = User.query.get_or_404(id)
    
    # Get all assigned bookings
    bookings = Booking.query.filter_by(employee_id=employee.id).order_by(Booking.created_at.desc()).all()
    
    # Get all assigned subscriptions
    subscriptions = Subscription.query.filter_by(employee_id=employee.id).all()
    
    # Get work schedule
    schedules = employee.schedules.all()
    
    # Get assigned neighborhoods
    neighborhoods = employee.neighborhoods
    
    # Calculate statistics
    total_bookings = len(bookings)
    completed_bookings = len([b for b in bookings if b.status == 'completed'])
    active_subscriptions = len([s for s in subscriptions if s.status == 'active'])
    
    # Calculate earnings from completed bookings
    total_earnings = sum([b.service.price for b in bookings if b.service and b.status == 'completed']) if bookings else 0
    
    stats = {
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'pending_bookings': len([b for b in bookings if b.status in ['pending', 'assigned', 'en_route', 'in_progress']]),
        'active_subscriptions': active_subscriptions,
        'total_subscriptions': len(subscriptions),
        'total_earnings': total_earnings,
        'assigned_neighborhoods': len(neighborhoods)
    }
    
    # Format schedule for display
    days_map = {6: 'الأحد', 0: 'الاثنين', 1: 'الثلاثاء', 2: 'الأربعاء', 3: 'الخميس', 4: 'الجمعة', 5: 'السبت'}
    formatted_schedules = []
    for schedule in schedules:
        formatted_schedules.append({
            'day': days_map.get(schedule.day_of_week, ''),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M')
        })
    
    return render_template('admin/employee_stats.html',
                         employee=employee,
                         stats=stats,
                         bookings=bookings,
                         subscriptions=subscriptions,
                         neighborhoods=neighborhoods,
                         schedules=formatted_schedules)

# --- Customer Management ---
@bp.route('/customers')
def customers():
    search_query = request.args.get('q', '').strip()
    query = User.query.filter_by(role='customer')
    
    if search_query:
        query = query.filter(
            or_(
                User.username.ilike(f'%{search_query}%'),
                User.phone.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
        
    customers = query.order_by(User.id.desc()).all()
    
    # Calculate stats for each customer
    for customer in customers:
        # Count vehicles
        customer.vehicle_count = customer.vehicles.count()
        
        # Get last purchase date from bookings
        last_booking = Booking.query.filter_by(customer_id=customer.id).order_by(Booking.created_at.desc()).first()
        customer.last_purchase_date = last_booking.created_at if last_booking else None
        
    return render_template('admin/customers.html', customers=customers)

@bp.route('/customers/<int:id>/reset-password', methods=['POST'])
def reset_customer_password(id):
    customer = User.query.get_or_404(id)
    new_password = request.form.get('new_password', '123456')
    customer.set_password(new_password)
    db.session.commit()
    flash(f'تم تغيير كلمة السر للعميل {customer.username}')
    return redirect(url_for('admin.customers'))

@bp.route('/customers/<int:id>/add-points', methods=['POST'])
def add_points(id):
    customer = User.query.get_or_404(id)
    points = int(request.form.get('points', 0))
    customer.points = (customer.points or 0) + points
    db.session.commit()
    action = 'إضافة' if points >= 0 else 'خصم'
    flash(f'تم {action} {abs(points)} نقطة للعميل {customer.username}')
    return redirect(url_for('admin.customers'))

@bp.route('/customers/<int:id>/update-washes', methods=['POST'])
def update_washes(id):
    customer = User.query.get_or_404(id)
    washes = int(request.form.get('washes', 0))
    customer.free_washes = (customer.free_washes or 0) + washes
    db.session.commit()
    action = 'إضافة' if washes >= 0 else 'خصم'
    flash(f'تم {action} {abs(washes)} غسلة مجانية للعميل {customer.username}')
    return redirect(url_for('admin.customers'))

@bp.route('/customers/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    """Delete customer and all related data"""
    from app.models import Vehicle
    
    customer = User.query.get_or_404(id)
    
    # Verify customer role
    if customer.role != 'customer':
        flash('لا يمكن حذف هذا المستخدم', 'error')
        return redirect(url_for('admin.customers'))
    
    # Delete related data in correct order
    # 1. Delete vehicles
    Vehicle.query.filter_by(user_id=customer.id).delete()
    
    # 2. Delete booking products first, then bookings
    for booking in Booking.query.filter_by(customer_id=customer.id).all():
        BookingProduct.query.filter_by(booking_id=booking.id).delete()
        db.session.delete(booking)
    
    # 3. Update bookings where customer is employee (set to NULL)
    Booking.query.filter_by(employee_id=customer.id).update({'employee_id': None})
    
    # 4. Delete subscriptions
    Subscription.query.filter_by(customer_id=customer.id).delete()
    
    # 5. Delete notifications
    Notification.query.filter_by(user_id=customer.id).delete()
    
    # 6. Delete push subscriptions
    PushSubscription.query.filter_by(user_id=customer.id).delete()
    
    # Finally, delete the customer
    username = customer.username
    db.session.delete(customer)
    db.session.commit()
    
    flash(f'تم حذف العميل {username} وجميع بياناته بنجاح', 'success')
    return redirect(url_for('admin.customers'))


@bp.route('/customers/<int:id>/stats')
def customer_stats(id):
    customer = User.query.get_or_404(id)
    
    # Get all bookings for this customer
    bookings = Booking.query.filter_by(customer_id=customer.id).order_by(Booking.created_at.desc()).all()
    
    # Get all subscriptions for this customer  
    subscriptions = Subscription.query.filter_by(customer_id=customer.id).all()
    
    # Get all vehicles
    vehicles = customer.vehicles.all()
    
    # Calculate statistics
    total_bookings = len(bookings)
    completed_bookings = len([b for b in bookings if b.status == 'completed'])
    
    # Calculate accurate total spent including discounts and products
    total_spent = 0
    total_products_purchased = 0
    total_products_value = 0
    total_services_value = 0
    
    for booking in bookings:
        if booking.status == 'completed':
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
            
            # Calculate final service price
            final_service_price = service_price - discount_amount
            total_services_value += final_service_price
            
            # Calculate products total
            products_total = sum([bp.product.price * bp.quantity for bp in booking.products])
            total_products_purchased += sum([bp.quantity for bp in booking.products])
            total_products_value += products_total
            
            # Add to total spent
            total_spent += final_service_price + products_total
    
    stats = {
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'pending_bookings': len([b for b in bookings if b.status in ['pending', 'assigned', 'en_route', 'in_progress']]),
        'total_spent': total_spent,
        'total_services_value': total_services_value,
        'total_products_purchased': total_products_purchased,
        'total_products_value': total_products_value,
        'points': customer.points or 0,
        'free_washes': customer.free_washes or 0,
        'total_vehicles': len(vehicles)
    }
    
    return render_template('admin/customer_stats.html', 
                         customer=customer, 
                         stats=stats, 
                         bookings=bookings, 
                         vehicles=vehicles)

@bp.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    customer = User.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update customer information
        customer.username = request.form.get('username')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        
        # Update password if provided
        new_password = request.form.get('password')
        if new_password and new_password.strip():
            customer.set_password(new_password)
        
        db.session.commit()
        flash(f'تم تحديث معلومات العميل {customer.username} بنجاح!')
        return redirect(url_for('admin.customers'))
    
    return render_template('admin/edit_customer.html', customer=customer)

@bp.route('/ratings')
def ratings():
    # Filters
    employee_id = request.args.get('employee_id')
    period = request.args.get('period', 'all')
    
    query = Booking.query.filter(Booking.rating.isnot(None)).order_by(Booking.rating_date.desc())
    
    if employee_id:
        query = query.filter(Booking.employee_id == int(employee_id))
        
    if period != 'all':
        today = date.today()
        if period == 'today':
            query = query.filter(func.date(Booking.rating_date) == today)
        elif period == 'month':
            query = query.filter(
                extract('year', Booking.rating_date) == today.year,
                extract('month', Booking.rating_date) == today.month
            )
        elif period == 'year':
            query = query.filter(extract('year', Booking.rating_date) == today.year)
            
    ratings = query.all()
    employees = User.query.filter_by(role='employee').all()
    
    return render_template('admin/ratings.html', ratings=ratings, employees=employees)

@bp.route('/customers/export')
def export_customers():
    try:
        import io
        from flask import send_file
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        
        customers = User.query.filter_by(role='customer').all()
        
        # Create Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "العملاء"
        ws.sheet_view.rightToLeft = True  # Enable RTL
        
        # Headers
        headers = ['#', 'الاسم', 'رقم الجوال', 'البريد الإلكتروني', 'الغسلات المجانية', 'نقاط الولاء', 'عدد السيارات', 'تاريخ اخر عملية شراء']
        ws.append(headers)
        
        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4DA8DA", end_color="4DA8DA", fill_type="solid")
        alignment = Alignment(horizontal="center", vertical="center")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # Apply style to headers
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment
            cell.border = border
            
        # Data
        for customer in customers:
            # Count vehicles
            vehicle_count = customer.vehicles.count()
            
            # Get last purchase date - with fallback
            try:
                last_booking = Booking.query.filter_by(customer_id=customer.id).order_by(Booking.date.desc()).first()
                if last_booking:
                    # Try created_at first, fallback to date
                    if hasattr(last_booking, 'created_at') and last_booking.created_at:
                        last_purchase = last_booking.created_at.strftime('%Y-%m-%d')
                    else:
                        last_purchase = last_booking.date.strftime('%Y-%m-%d') if last_booking.date else '-'
                else:
                    last_purchase = '-'
            except Exception as e:
                last_purchase = '-'
            
            row = [
                customer.id,
                customer.username,
                customer.phone or '-',
                customer.email or '-',
                customer.free_washes or 0,
                customer.points or 0,
                vehicle_count,
                last_purchase
            ]
            ws.append(row)
            
            # Apply style to data rows
            for cell in ws[ws.max_row]:
                cell.alignment = alignment
                cell.border = border

        # Auto-adjust column widths
        for column_cells in ws.columns:
            length = max(len(str(cell.value) or "") for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = length + 5

        # Save to buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='customers.xlsx'
        )
    except ImportError:
        # openpyxl not installed - fallback to CSV
        flash('خطأ: مكتبة openpyxl غير مثبتة. يرجى تثبيتها أولاً.', 'error')
        return redirect(url_for('admin.customers'))
    except Exception as e:
        # Log the error and show user-friendly message
        flash(f'حدث خطأ أثناء تصدير البيانات: {str(e)}', 'error')
        return redirect(url_for('admin.customers'))


# --- Service Management ---
@bp.route('/services')
def services():
    services_list = Service.query.all()
    services_data = []
    
    for service in services_list:
        # Calculate completed bookings count
        completed_bookings_count = Booking.query.filter_by(service_id=service.id, status='completed').count()
        
        # Calculate total revenue
        total_revenue = completed_bookings_count * service.price
        
        services_data.append({
            'service': service,
            'completed_bookings_count': completed_bookings_count,
            'total_revenue': total_revenue
        })
        
    return render_template('admin/services.html', services=services_data)

@bp.route('/services/add', methods=['GET', 'POST'])
def add_service():
    form = ServiceForm()
    if form.validate_on_submit():
        try:
            service = Service(name_ar=form.name_ar.data, name_en=form.name_en.data, 
                              price=form.price.data, duration=form.duration.data, 
                              description=form.description.data,
                              includes_free_wash=form.includes_free_wash.data)
            db.session.add(service)
            db.session.commit()
            flash('تم إضافة الخدمة بنجاح', 'success')
            return redirect(url_for('admin.services'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'error')
    elif request.method == 'POST':
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    return render_template('admin/service_form.html', form=form, title='إضافة خدمة')

@bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
def edit_service(id):
    service = Service.query.get_or_404(id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        flash('تم تعديل الخدمة')
        return redirect(url_for('admin.services'))
    return render_template('admin/service_form.html', form=form, title='تعديل خدمة')

@bp.route('/services/delete/<int:id>')
def delete_service(id):
    service = Service.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('تم حذف الخدمة')
    return redirect(url_for('admin.services'))

# --- Vehicle Size Management ---
@bp.route('/vehicle-sizes')
def vehicle_sizes():
    sizes = VehicleSize.query.all()
    return render_template('admin/vehicle_sizes.html', vehicle_sizes=sizes)

@bp.route('/vehicle-sizes/add', methods=['GET', 'POST'])
def add_vehicle_size():
    form = VehicleSizeForm()
    if form.validate_on_submit():
        size = VehicleSize(
            name_ar=form.name_ar.data,
            name_en=form.name_en.data,
            price_adjustment=form.price_adjustment.data,
            is_active=form.is_active.data
        )
        db.session.add(size)
        db.session.commit()
        flash('تم إضافة حجم السيارة بنجاح')
        return redirect(url_for('admin.vehicle_sizes'))
    return render_template('admin/vehicle_size_form.html', form=form, title='إضافة حجم سيارة')

@bp.route('/vehicle-sizes/edit/<int:id>', methods=['GET', 'POST'])
def edit_vehicle_size(id):
    size = VehicleSize.query.get_or_404(id)
    form = VehicleSizeForm(obj=size)
    if form.validate_on_submit():
        size.name_ar = form.name_ar.data
        size.name_en = form.name_en.data
        size.price_adjustment = form.price_adjustment.data
        size.is_active = form.is_active.data
        db.session.commit()
        flash('تم تعديل حجم السيارة بنجاح')
        return redirect(url_for('admin.vehicle_sizes'))
    return render_template('admin/vehicle_size_form.html', form=form, title='تعديل حجم سيارة')

@bp.route('/vehicle-sizes/delete/<int:id>')
def delete_vehicle_size(id):
    size = VehicleSize.query.get_or_404(id)
    db.session.delete(size)
    db.session.commit()
    flash('تم حذف حجم السيارة')
    return redirect(url_for('admin.vehicle_sizes'))

# --- Products Management ---
@bp.route('/products')
def products():
    from app.models import ProductStock
    all_products = Product.query.all()
    products_data = []
    total_sales_revenue = 0
    
    for product in all_products:
        # Get total quantity sold (only for completed bookings)
        sold_quantity = db.session.query(func.sum(BookingProduct.quantity))\
            .join(Booking, BookingProduct.booking_id == Booking.id)\
            .filter(
                BookingProduct.product_id == product.id,
                Booking.status == 'completed'
            ).scalar() or 0
        
        revenue = sold_quantity * product.price
        total_sales_revenue += revenue
        
        products_data.append({
            'product': product,
            'sold_quantity': sold_quantity,
            'revenue': revenue,
            'stock': product.stock_quantity
        })
    
    # Get cities for location stock management
    # For supervisors, only show their assigned areas
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        supervisor_city_ids = set()
        
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
            for n in current_user.supervisor_neighborhoods:
                supervisor_city_ids.add(n.city_id)
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_city_ids.add(city.id)
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        cities = City.query.filter(City.id.in_(supervisor_city_ids), City.is_active==True).all()
        # Only include neighborhoods in supervisor's scope
        cities_json = json.dumps([{
            'id': c.id,
            'name_ar': c.name_ar,
            'neighborhoods': [{'id': n.id, 'name_ar': n.name_ar} for n in c.neighborhoods if n.id in supervisor_neighborhood_ids]
        } for c in cities])
    else:
        cities = City.query.filter_by(is_active=True).all()
        cities_json = json.dumps([{
            'id': c.id,
            'name_ar': c.name_ar,
            'neighborhoods': [{'id': n.id, 'name_ar': n.name_ar} for n in c.neighborhoods]
        } for c in cities])
    
    return render_template('admin/products.html', products=products_data, 
                           total_sales_revenue=total_sales_revenue, cities=cities, cities_json=cities_json)

@bp.route('/products/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    """Update product stock - either global or per location"""
    from app.models import ProductStock
    
    product = Product.query.get_or_404(product_id)
    stock = request.form.get('stock', 0, type=int)
    city_id = request.form.get('city_id', type=int)
    neighborhood_id = request.form.get('neighborhood_id', type=int)
    
    if city_id:
        # Location-based stock update
        existing = ProductStock.query.filter_by(
            product_id=product_id,
            city_id=city_id,
            neighborhood_id=neighborhood_id if neighborhood_id else None
        ).first()
        
        if existing:
            existing.quantity = stock
        else:
            new_stock = ProductStock(
                product_id=product_id,
                city_id=city_id,
                neighborhood_id=neighborhood_id if neighborhood_id else None,
                quantity=stock
            )
            db.session.add(new_stock)
        
        flash(f'تم تحديث المخزون للموقع المحدد')
    else:
        # Global stock update
        product.stock_quantity = stock
        flash('تم تحديث المخزون العام')
    
    db.session.commit()
    return redirect(url_for('admin.products'))

@bp.route('/products/location_stock/<int:product_id>')
def get_location_stock(product_id):
    """Get all location stocks for a product"""
    from app.models import ProductStock
    
    stocks = ProductStock.query.filter_by(product_id=product_id).all()
    result = []
    
    for s in stocks:
        result.append({
            'id': s.id,
            'city_id': s.city_id,
            'city_name': s.city.name_ar if s.city else '',
            'neighborhood_id': s.neighborhood_id,
            'neighborhood_name': s.neighborhood.name_ar if s.neighborhood else 'كل الأحياء',
            'quantity': s.quantity
        })
    
    return jsonify(result)

@bp.route('/products/add', methods=['GET', 'POST'])
def add_product():
    import os
    from werkzeug.utils import secure_filename
    
    form = ProductForm()
    if form.validate_on_submit():
        image_url = None
        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join('app', 'static', 'uploads', filename)
            file.save(filepath)
            image_url = f"/static/uploads/{filename}"
        
        product = Product(
            name_ar=form.name_ar.data,
            name_en=form.name_en.data,
            price=float(form.price.data),
            image_url=image_url
        )
        db.session.add(product)
        db.session.commit()
        flash('تم إضافة المنتج بنجاح')
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', form=form, title='إضافة منتج')


# --- Location Management ---
@bp.route('/locations')
def locations():
    cities = City.query.all()

    city_stats = []
    for city in cities:
        neighborhood_count = city.neighborhoods.count()

        city_neighborhood_ids = [n.id for n in city.neighborhoods]

        if city_neighborhood_ids:
            bookings_q = Booking.query.filter(Booking.neighborhood_id.in_(city_neighborhood_ids))
            booking_count = bookings_q.count()
            completed_bookings = bookings_q.filter_by(status='completed').all()
        else:
            booking_count = 0
            completed_bookings = []

        revenue = sum(b.service.price for b in completed_bookings if b.service)

        city_stats.append({
            'city': city,
            'neighborhood_count': neighborhood_count,
            'booking_count': booking_count,
            'revenue': revenue,
        })

    return render_template('admin/locations.html', city_stats=city_stats)

@bp.route('/locations/city/add', methods=['GET', 'POST'])
def add_city():
    form = CityForm()
    if form.validate_on_submit():
        city = City(name_ar=form.name_ar.data, name_en=form.name_en.data, is_active=form.is_active.data)
        db.session.add(city)
        db.session.commit()
        flash('تم إضافة المدينة بنجاح')
        return redirect(url_for('admin.locations'))
    return render_template('admin/location_form.html', form=form, title='إضافة مدينة', type='city')

@bp.route('/locations/city/edit/<int:id>', methods=['GET', 'POST'])
def edit_city(id):
    city = City.query.get_or_404(id)
    form = CityForm(obj=city)
    if form.validate_on_submit():
        form.populate_obj(city)
        db.session.commit()
        flash('تم تعديل المدينة')
        return redirect(url_for('admin.locations'))
    return render_template('admin/location_form.html', form=form, title='تعديل مدينة', type='city')

@bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    import os
    from werkzeug.utils import secure_filename
    
    product = Product.query.get_or_404(id)
    form = ProductForm()
    
    if form.validate_on_submit():
        product.name_ar = form.name_ar.data
        product.name_en = form.name_en.data
        product.price = float(form.price.data)
        
        # Handle image upload
        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join('app', 'static', 'uploads', filename)
            file.save(filepath)
            product.image_url = f"/static/uploads/{filename}"
        
        db.session.commit()
        flash('تم تحديث المنتج')
        return redirect(url_for('admin.products'))
    elif request.method == 'GET':
        form.name_ar.data = product.name_ar
        form.name_en.data = product.name_en
        form.price.data = str(product.price)
    
    return render_template('admin/product_form.html', form=form, title='تعديل منتج', product=product)


@bp.route('/products/delete/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('تم حذف المنتج')
    return redirect(url_for('admin.products'))

@bp.route('/products/stats/<int:id>')
def product_stats(id):
    product = Product.query.get_or_404(id)
    
    # Calculate total sold quantity
    sold_quantity = db.session.query(func.sum(BookingProduct.quantity))\
        .join(Booking, BookingProduct.booking_id == Booking.id)\
        .filter(
            BookingProduct.product_id == product.id,
            Booking.status == 'completed'
        ).scalar() or 0
        
    # Calculate total revenue
    total_revenue = sold_quantity * product.price
    
    # Get recent bookings for this product
    recent_bookings = db.session.query(Booking, BookingProduct.quantity)\
        .join(BookingProduct, Booking.id == BookingProduct.booking_id)\
        .filter(BookingProduct.product_id == product.id)\
        .order_by(Booking.date.desc(), Booking.time.desc())\
        .limit(20).all()
        
    return render_template('admin/product_stats.html', product=product, sold_quantity=sold_quantity, total_revenue=total_revenue, recent_bookings=recent_bookings)

# --- Location Management ---
    if form.validate_on_submit():
        form.populate_obj(city)
        db.session.commit()
        flash('تم تعديل المدينة')
        return redirect(url_for('admin.locations'))
    return render_template('admin/location_form.html', form=form, title='تعديل مدينة', type='city')

@bp.route('/locations/neighborhood/add/<int:city_id>', methods=['GET', 'POST'])
def add_neighborhood(city_id):
    city = City.query.get_or_404(city_id)
    form = NeighborhoodForm()
    form.city_id.choices = [(c.id, c.name_ar) for c in City.query.all()]
    form.city_id.data = city.id
    
    if form.validate_on_submit():
        neighborhood = Neighborhood(city_id=form.city_id.data, name_ar=form.name_ar.data, 
                                    name_en=form.name_en.data, is_active=form.is_active.data)
        db.session.add(neighborhood)
        db.session.commit()
        flash('تم إضافة الحي بنجاح')
        return redirect(url_for('admin.locations'))
    return render_template('admin/location_form.html', form=form, title='إضافة حي', type='neighborhood')

@bp.route('/locations/neighborhood/edit/<int:id>', methods=['GET', 'POST'])
def edit_neighborhood(id):
    neighborhood = Neighborhood.query.get_or_404(id)
    form = NeighborhoodForm(obj=neighborhood)
    form.city_id.choices = [(c.id, c.name_ar) for c in City.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(neighborhood)
        db.session.commit()
        flash('تم تعديل الحي')
        return redirect(url_for('admin.locations'))
    return render_template('admin/location_form.html', form=form, title='تعديل حي', type='neighborhood')

@bp.route('/locations/city/delete/<int:id>')
def delete_city(id):
    city = City.query.get_or_404(id)
    # Check if city has neighborhoods
    if city.neighborhoods.count() > 0:
        flash('لا يمكن حذف المدينة لأنها تحتوي على أحياء. احذف الأحياء أولاً.')
        return redirect(url_for('admin.locations'))
    
    db.session.delete(city)
    db.session.commit()
    flash('تم حذف المدينة بنجاح')
    return redirect(url_for('admin.locations'))

@bp.route('/locations/neighborhood/delete/<int:id>')
def delete_neighborhood(id):
    neighborhood = Neighborhood.query.get_or_404(id)
    db.session.delete(neighborhood)
    db.session.commit()
    flash('تم حذف الحي بنجاح')
    return redirect(url_for('admin.locations'))

# --- Subscription Package Management ---
@bp.route('/packages')
def packages():
    packages = SubscriptionPackage.query.all()
    return render_template('admin/packages.html', packages=packages)

@bp.route('/packages/add', methods=['GET', 'POST'])
def add_package():
    form = SubscriptionPackageForm()
    if form.validate_on_submit():
        package = SubscriptionPackage(
            name_ar=form.name_ar.data,
            name_en=form.name_en.data,
            price=float(form.price.data),
            wash_count=int(form.wash_count.data),
            duration_days=int(form.duration_days.data),
            description=form.description.data,
            is_active=True
        )
        db.session.add(package)
        db.session.commit()
        flash('تم إضافة الباقة بنجاح')
        return redirect(url_for('admin.packages'))
    return render_template('admin/package_form.html', form=form, title='إضافة باقة اشتراك')

@bp.route('/packages/edit/<int:id>', methods=['GET', 'POST'])
def edit_package(id):
    package = SubscriptionPackage.query.get_or_404(id)
    form = SubscriptionPackageForm()
    if form.validate_on_submit():
        package.name_ar = form.name_ar.data
        package.name_en = form.name_en.data
        package.price = float(form.price.data)
        package.wash_count = int(form.wash_count.data)
        package.duration_days = int(form.duration_days.data)
        package.description = form.description.data
        db.session.commit()
        flash('تم تعديل الباقة')
        return redirect(url_for('admin.packages'))
    elif request.method == 'GET':
        form.name_ar.data = package.name_ar
        form.name_en.data = package.name_en
        form.price.data = str(package.price)
        form.wash_count.data = str(package.wash_count)
        form.duration_days.data = str(package.duration_days)
        form.description.data = package.description
    return render_template('admin/package_form.html', form=form, title='تعديل باقة اشتراك')

@bp.route('/packages/delete/<int:id>')
def delete_package(id):
    package = SubscriptionPackage.query.get_or_404(id)
    db.session.delete(package)
    db.session.commit()
    flash('تم حذف الباقة')
    return redirect(url_for('admin.packages'))

# --- Subscription Requests Management ---
@bp.route('/subscriptions')
@login_required
def subscriptions():
    import json
    status = request.args.get('status', 'active')
    search_query = request.args.get('search', '').strip()
    
    subscriptions_query = Subscription.query
    
    # Filter by status
    if status != 'all':
        subscriptions_query = subscriptions_query.filter_by(status=status)
        
    # Filter for supervisors
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        if supervisor_neighborhood_ids:
            subscriptions_query = subscriptions_query.filter(Subscription.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            subscriptions_query = subscriptions_query.filter_by(id=-1) # Empty result
        
    # Search filter
    if search_query:
        subscriptions_query = subscriptions_query.join(User, User.id == Subscription.customer_id).filter(
            (User.username.contains(search_query)) | 
            (User.phone.contains(search_query))
        )
    
    subscriptions_result = subscriptions_query.order_by(Subscription.created_at.desc()).all()
    
    # Get counts for tabs
    pending_count = Subscription.query.filter_by(status='pending').count()
    active_count = Subscription.query.filter_by(status='active').count()
    rejected_count = Subscription.query.filter_by(status='rejected').count()
    expired_count = Subscription.query.filter_by(status='expired').count()
    
    # Prepare JSON data for JavaScript
    subs_json = json.dumps([{
        'id': s.id,
        'customer_id': s.customer_id,
        'employee_id': s.employee_id,
        'neighborhood_id': s.neighborhood_id,
        'city_id': s.neighborhood.city_id if s.neighborhood else None,
        'remaining_washes': s.remaining_washes or 0,
        'end_date': s.end_date.isoformat() if s.end_date else None
    } for s in subscriptions_result])
    
    cities = City.query.all()
    cities_json = json.dumps([{
        'id': c.id,
        'name_ar': c.name_ar,
        'neighborhoods': [{'id': n.id, 'name_ar': n.name_ar} for n in c.neighborhoods]
    } for c in cities])
    
    employees = User.query.filter_by(role='employee').all()
    customers = User.query.filter_by(role='customer').all()
    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    
    return render_template('admin/subscriptions.html',
                          subscriptions=subscriptions_result,
                          current_status=status,
                          search_query=search_query,
                          pending_count=pending_count,
                          active_count=active_count,
                          rejected_count=rejected_count,
                          expired_count=expired_count,
                          subscriptions_json=subs_json,
                          cities=cities,
                          cities_json=cities_json,
                          employees=employees,
                          customers=customers,
                          packages=packages)

@bp.route('/subscriptions/create', methods=['POST'])
def create_subscription():
    from datetime import datetime, timedelta
    
    customer_id = request.form.get('customer_id')
    package_id = request.form.get('package_id')
    employee_id = request.form.get('employee_id')
    neighborhood_id = request.form.get('neighborhood_id')
    discount = float(request.form.get('discount', 0))
    
    # Validate supervisor scope
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        # Check if the neighborhood is within supervisor's scope
        if int(neighborhood_id) not in supervisor_neighborhood_ids:
            flash('خطأ: لا يمكنك إضافة اشتراك خارج نطاق منطقتك المحددة', 'error')
            return redirect(url_for('admin.subscriptions'))
    
    package = SubscriptionPackage.query.get(package_id)
    if not package:
        flash('الباقة غير موجودة')
        return redirect(url_for('admin.subscriptions'))
    
    # Create subscription (employee is now optional - booking will find available employee)
    subscription = Subscription(
        customer_id=int(customer_id),
        employee_id=int(employee_id) if employee_id else None,
        neighborhood_id=int(neighborhood_id),
        package_id=int(package_id),
        remaining_washes=int(package.wash_count),
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(days=int(package.duration_days))).date(),
        status='active'
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    flash(f'تم إضافة الاشتراك بنجاح (الخصم: {discount}%)')
    return redirect(url_for('admin.subscriptions', status='active'))

@bp.route('/subscriptions/<int:id>/approve', methods=['POST'])
def approve_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    employee_id = request.form.get('employee_id')
    
    # Employee is now optional - bookings will find available employee in neighborhood
    subscription.status = 'active'
    if employee_id:
        subscription.employee_id = int(employee_id)
    
    # Set remaining washes from package
    if subscription.package:
        subscription.remaining_washes = int(subscription.package.wash_count)
    
    db.session.commit()
    flash('تم قبول الاشتراك بنجاح')
    return redirect(url_for('admin.subscriptions', status='active'))

@bp.route('/subscriptions/<int:id>/reject')
def reject_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    subscription.status = 'rejected'
    db.session.commit()
    flash('تم رفض الطلب')
    return redirect(url_for('admin.subscriptions', status='rejected'))

@bp.route('/subscriptions/<int:id>/reassign', methods=['POST'])
def reassign_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    employee_id = request.form.get('employee_id')
    
    if not employee_id:
        flash('يجب اختيار موظف')
        return redirect(url_for('admin.subscriptions', status='active'))
    
    subscription.employee_id = int(employee_id)
    db.session.commit()
    flash('تم إعادة إسناد الاشتراك بنجاح')
    return redirect(url_for('admin.subscriptions', status='active'))

@bp.route('/subscriptions/<int:id>/edit', methods=['POST'])
def edit_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    
    # Update employee
    employee_id = request.form.get('employee_id')
    if employee_id:
        subscription.employee_id = int(employee_id)
    
    # Update location
    neighborhood_id = request.form.get('neighborhood_id')
    if neighborhood_id:
        subscription.neighborhood_id = int(neighborhood_id)
    
    # Update remaining washes
    remaining_washes = request.form.get('remaining_washes')
    if remaining_washes:
        subscription.remaining_washes = int(remaining_washes)
    
    # Update end date
    end_date_str = request.form.get('end_date')
    if end_date_str:
        from datetime import datetime
        subscription.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    db.session.commit()
    flash('تم تحديث الاشتراك بنجاح')
    return redirect(url_for('admin.subscriptions', status='active'))

@bp.route('/subscriptions/<int:id>/delete')
def delete_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    db.session.delete(subscription)
    db.session.commit()
    flash('تم حذف الاشتراك بنجاح')
    return redirect(url_for('admin.subscriptions', status='active'))

@bp.route('/subscriptions/whatsapp/<int:id>')
def whatsapp_customer(id):
    subscription = Subscription.query.get_or_404(id)
    customer = subscription.customer
    
    # Format phone number for WhatsApp (remove + and spaces)
    phone = customer.phone.replace('+', '').replace(' ', '') if customer.phone else ''
    
    # Create message
    message = f"مرحباً {customer.username}، نود التواصل معك بخصوص طلب الاشتراك رقم #{subscription.id}"
    
    # WhatsApp URL
    whatsapp_url = f"https://wa.me/{phone}?text={quote(message)}"
    
    return redirect(whatsapp_url)

# API endpoint for getting employees by neighborhood
@bp.route('/api/employees-by-neighborhood/<int:neighborhood_id>')
def employees_by_neighborhood(neighborhood_id):
    from app.models import User, employee_neighborhoods
    
    # Get employees assigned to this neighborhood
    employees = User.query.join(employee_neighborhoods).filter(
        employee_neighborhoods.c.neighborhood_id == neighborhood_id,
        User.role == 'employee'
    ).all()
    
    return jsonify([{'id': emp.id, 'username': emp.username} for emp in employees])

# --- Booking Management ---
@bp.route('/bookings')
def bookings():
    import json
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    employee_filter = request.args.get('employee', 'all')
    date_filter = request.args.get('date', '')
    search_query = request.args.get('q', '').strip()
    
    query = Booking.query
    
    # Filter for supervisors
    supervisor_neighborhood_ids = []
    if current_user.role == 'supervisor':
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        if supervisor_neighborhood_ids:
            query = query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            query = query.filter_by(id=-1)  # Empty result
    
    if status_filter == 'current':
        query = query.filter(Booking.status.in_(['pending', 'assigned', 'en_route', 'arrived', 'in_progress']))
    elif status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if employee_filter != 'all':
        query = query.filter_by(employee_id=int(employee_filter))
    if date_filter:
        from datetime import datetime
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(date=filter_date)
        
    # Apply search
    if search_query:
        # Check if search query is a number (for ID search)
        if search_query.isdigit():
             query = query.join(User, Booking.customer_id == User.id).filter(
                or_(
                    Booking.id == int(search_query),
                    User.phone.ilike(f'%{search_query}%')
                )
            )
        else:
            query = query.join(User, Booking.customer_id == User.id).filter(
                User.username.ilike(f'%{search_query}%')
            )
            
    bookings_list = query.order_by(Booking.id.desc()).all()
    
    # Filter cities and neighborhoods for supervisor
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            # Get cities that contain the supervisor's neighborhoods
            city_ids = set()
            for neighborhood in Neighborhood.query.filter(Neighborhood.id.in_(supervisor_neighborhood_ids)).all():
                city_ids.add(neighborhood.city_id)
            
            cities = City.query.filter(City.id.in_(city_ids)).all()
        else:
            cities = []
    else:
        cities = City.query.all()
    
    cities_json = json.dumps([{
        'id': c.id,
        'name_ar': c.name_ar,
        'neighborhoods': [{'id': n.id, 'name_ar': n.name_ar} for n in c.neighborhoods if current_user.role != 'supervisor' or n.id in supervisor_neighborhood_ids]
    } for c in cities])
    
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Filter employees for supervisor
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            employees = User.query.filter_by(role='employee').join(User.neighborhoods).filter(Neighborhood.id.in_(supervisor_neighborhood_ids)).distinct().all()
        else:
            employees = []
    else:
        employees = User.query.filter_by(role='employee').all()
    
    customers = User.query.filter_by(role='customer').all()
    services = Service.query.all()
    
    # Get counts for status tabs
    current_statuses = ['pending', 'assigned', 'en_route', 'arrived', 'in_progress']
    current_count = Booking.query.filter(Booking.status.in_(current_statuses)).count()
    completed_count = Booking.query.filter_by(status='completed').count()
    cancelled_count = Booking.query.filter_by(status='cancelled').count()
    
    return render_template('admin/bookings.html', bookings=bookings_list, employees=employees, 
                           status_filter=status_filter, employee_filter=employee_filter, date_filter=date_filter,
                           customers=customers, services=services, cities=cities, cities_json=cities_json, today=today,
                           current_count=current_count, completed_count=completed_count, cancelled_count=cancelled_count)

@bp.route('/bookings/create', methods=['POST'])
def create_booking():
    from datetime import datetime, time as dt_time
    
    customer_id = request.form.get('customer_id')
    service_id = request.form.get('service_id')
    employee_id = request.form.get('employee_id')
    neighborhood_id = request.form.get('neighborhood_id')
    date = request.form.get('date')
    time_str = request.form.get('time')
    discount = float(request.form.get('discount', 0))
    
    # Validate supervisor scope
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        # Check if the neighborhood is within supervisor's scope
        if int(neighborhood_id) not in supervisor_neighborhood_ids:
            flash('خطأ: لا يمكنك إضافة حجز خارج نطاق منطقتك المحددة', 'error')
            return redirect(url_for('admin.bookings'))
    
    # Convert time string to time object
    hour, minute = map(int, time_str.split(':'))
    time_obj = dt_time(hour, minute)
    
    # If employee is assigned, status should be 'assigned', otherwise 'pending'
    booking_status = 'assigned' if employee_id else 'pending'
    
    booking = Booking(
        customer_id=int(customer_id), 
        service_id=int(service_id), 
        employee_id=int(employee_id) if employee_id else None,
        neighborhood_id=int(neighborhood_id) if neighborhood_id else None,
        date=datetime.strptime(date, '%Y-%m-%d').date(), 
        time=time_obj,
        status=booking_status
    )
    db.session.add(booking)
    db.session.commit()
    
    # Notify employee if assigned
    if employee_id:
        employee = User.query.get(int(employee_id))
        if employee:
            from app.notifications import send_push_notification
            notification_data = {
                "title": "حجز جديد تم تعيينه لك 🆕",
                "body": f"تم تعيين حجز جديد #{booking.id}\nالعميل: {booking.customer.username}\nالخدمة: {booking.service.name_ar}\nالموعد: {booking.date} {booking.time.strftime('%H:%M')}",
                "icon": "/static/images/logo.png",
                "badge": "/static/images/logo.png",
                "url": "/employee/bookings/active",
                "data": {
                    "booking_id": booking.id
                }
            }
            send_push_notification(employee, notification_data)
            
    flash(f'تم إضافة الحجز بنجاح (الخصم: {discount}%)')
    return redirect(url_for('admin.bookings'))

@bp.route('/api/available-slots/<int:employee_id>/<date>')
def get_available_slots(employee_id, date):
    from datetime import datetime, timedelta, time as dt_time
    
    # BOOKING DURATION: Each booking takes 90 minutes (1.5 hours)
    BOOKING_DURATION_MINUTES = 90
    
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    day_of_week = date_obj.weekday()
    
    print(f"[DEBUG] Looking for slots: employee_id={employee_id}, date={date}, day_of_week={day_of_week}")
    
    schedule = EmployeeSchedule.query.filter_by(
        employee_id=employee_id, 
        day_of_week=day_of_week, 
        is_active=True
    ).first()
    
    print(f"[DEBUG] Found schedule: {schedule}")
    if schedule:
        print(f"[DEBUG] Schedule details: day={schedule.day_of_week}, start={schedule.start_time}, end={schedule.end_time}")
    
    if not schedule:
        print(f"[DEBUG] No schedule found, returning empty")
        return jsonify([])
    
    # Get all bookings for this employee on this date
    bookings = Booking.query.filter_by(
        employee_id=employee_id,
        date=date_obj
    ).all()
    
    # Build set of blocked time ranges (each booking blocks 90 minutes)
    blocked_ranges = []
    for booking in bookings:
        booking_start = datetime.combine(date_obj, booking.time)
        booking_end = booking_start + timedelta(minutes=BOOKING_DURATION_MINUTES)
        blocked_ranges.append((booking_start, booking_end))
    
    print(f"[DEBUG] Blocked ranges: {[(r[0].time(), r[1].time()) for r in blocked_ranges]}")
    
    # Get current time if booking for today
    now = datetime.now()
    is_today = date_obj == now.date()
    current_time = now.time() if is_today else None
    
    print(f"[DEBUG] is_today={is_today}, current_time={current_time}")
    
    slots = []
    current = datetime.combine(date_obj, schedule.start_time)
    end = datetime.combine(date_obj, schedule.end_time)
    
    # Generate slots every 90 minutes
    while current < end:
        slot_end = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
        
        # Skip if slot would extend beyond working hours
        if slot_end > end:
            break
        
        time_str = current.strftime('%H:%M')
        slot_time = current.time()
        
        # Skip if it's today and the time has passed
        if is_today and current_time and slot_time <= current_time:
            print(f"[DEBUG] Skipping {time_str} - past time")
            current = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
            continue
        
        # Check if this slot overlaps with any blocked range
        slot_blocked = False
        for blocked_start, blocked_end in blocked_ranges:
            # Check if there's any overlap
            if current < blocked_end and slot_end > blocked_start:
                slot_blocked = True
                print(f"[DEBUG] Skipping {time_str} - conflicts with booking at {blocked_start.time()}")
                break
        
        if not slot_blocked:
            slots.append(time_str)
        
        current = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
    
    print(f"[DEBUG] Final slots: {slots}")
    return jsonify(slots)

@bp.route('/api/area-available-slots/<int:neighborhood_id>/<date>')
def get_area_available_slots(neighborhood_id, date):
    """Get all available time slots from all employees in a neighborhood"""
    from datetime import datetime, timedelta
    from app.models import employee_neighborhoods
    
    # BOOKING DURATION: Each booking takes 90 minutes (1.5 hours)
    BOOKING_DURATION_MINUTES = 90
    
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    day_of_week = date_obj.weekday()
    
    # Get current time if booking for today
    now = datetime.now()
    is_today = date_obj == now.date()
    current_time = now.time() if is_today else None
    
    # Get all employees in this neighborhood
    employees = User.query.join(employee_neighborhoods).filter(
        employee_neighborhoods.c.neighborhood_id == neighborhood_id,
        User.role == 'employee'
    ).all()
    
    # Collect all available slots from all employees
    all_slots = set()
    for emp in employees:
        schedule = EmployeeSchedule.query.filter_by(
            employee_id=emp.id,
            day_of_week=day_of_week,
            is_active=True
        ).first()
        
        if schedule:
            # Get bookings for this employee
            bookings = Booking.query.filter_by(
                employee_id=emp.id,
                date=date_obj
            ).all()
            
            # Build blocked ranges
            blocked_ranges = []
            for booking in bookings:
                booking_start = datetime.combine(date_obj, booking.time)
                booking_end = booking_start + timedelta(minutes=BOOKING_DURATION_MINUTES)
                blocked_ranges.append((booking_start, booking_end))
            
            current = datetime.combine(date_obj, schedule.start_time)
            end = datetime.combine(date_obj, schedule.end_time)
            
            while current < end:
                slot_end = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
                
                # Skip if slot would extend beyond working hours
                if slot_end > end:
                    break
                
                time_str = current.strftime('%H:%M')
                slot_time = current.time()
                
                # Skip if it's today and the time has passed
                if is_today and current_time and slot_time <= current_time:
                    current = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
                    continue
                
                # Check if this slot overlaps with any blocked range
                slot_blocked = False
                for blocked_start, blocked_end in blocked_ranges:
                    if current < blocked_end and slot_end > blocked_start:
                        slot_blocked = True
                        break
                
                if not slot_blocked:
                    all_slots.add(time_str)
                
                current = current + timedelta(minutes=BOOKING_DURATION_MINUTES)
    
    return jsonify(sorted(list(all_slots)))

def auto_assign_employee(neighborhood_id, date, time_str):
    """Automatically assign an available employee from the neighborhood"""
    from datetime import datetime, time as dt_time
    from app.models import employee_neighborhoods
    
    date_obj = datetime.strptime(date, '%Y-%m-%d').date() if isinstance(date, str) else date
    day_of_week = date_obj.weekday()
    
    # Convert time string to time object for comparison
    hour, minute = map(int, time_str.split(':'))
    time_obj = dt_time(hour, minute)
    
    # Get all employees in this neighborhood
    employees = User.query.join(employee_neighborhoods).filter(
        employee_neighborhoods.c.neighborhood_id == neighborhood_id,
        User.role == 'employee'
    ).all()
    
    available_employees = []
    for emp in employees:
        # Check if employee has schedule for this day
        schedule = EmployeeSchedule.query.filter_by(
            employee_id=emp.id,
            day_of_week=day_of_week,
            is_active=True
        ).first()
        
        if not schedule:
            continue
            
        # Check if time is within working hours
        if not (schedule.start_time <= time_obj < schedule.end_time):
            continue
        
        # Check if not already booked
        existing_booking = Booking.query.filter_by(
            employee_id=emp.id,
            date=date_obj,
            time=time_str
        ).first()
        
        if not existing_booking:
            # Count today's bookings for load balancing
            bookings_count = Booking.query.filter_by(
                employee_id=emp.id,
                date=date_obj
            ).count()
            available_employees.append((emp, bookings_count))
    
    if not available_employees:
        return None
    
    # Sort by bookings count (load balancing) and return employee with least bookings
    available_employees.sort(key=lambda x: x[1])
    return available_employees[0][0].id

@bp.route('/bookings/<int:id>/reassign', methods=['POST'])
def reassign_booking(id):
    """Reassign booking to a different employee in the same neighborhood"""
    from datetime import datetime, time as dt_time
    
    booking = Booking.query.get_or_404(id)
    new_employee_id = request.form.get('employee_id')
    new_time_str = request.form.get('time')  # Optional - can change time too
    
    if not new_employee_id:
        flash('يجب اختيار موظف')
        return redirect(url_for('admin.bookings'))
    
    # If time is being changed, convert and validate
    if new_time_str:
        hour, minute = map(int, new_time_str.split(':'))
        new_time = dt_time(hour, minute)
        
        # Check if new employee is available at new time
        existing = Booking.query.filter_by(
            employee_id=int(new_employee_id),
            date=booking.date,
            time=new_time_str
        ).first()
        
        if existing:
            flash('الموظف محجوز في هذا الوقت')
            return redirect(url_for('admin.bookings'))
        
        booking.time = new_time
    else:
        # Check availability at current time
        existing = Booking.query.filter_by(
            employee_id=int(new_employee_id),
            date=booking.date,
            time=booking.time.strftime('%H:%M')
        ).first()
        
        if existing:
            flash('الموظف محجوز في هذا الوقت')
            return redirect(url_for('admin.bookings'))
    
    booking.employee_id = int(new_employee_id)
    db.session.commit()
    flash('تم إعادة إسناد الحجز بنجاح')
    return redirect(url_for('admin.bookings'))

@bp.route('/bookings/<int:id>/cancel')
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    booking.status = 'cancelled'
    db.session.commit()
    flash('تم إلغاء الحجز')
    return redirect(url_for('admin.bookings'))

@bp.route('/bookings/<int:id>/delete', methods=['POST'])
def delete_booking(id):
    booking = Booking.query.get_or_404(id)
    db.session.delete(booking)
    db.session.commit()
    flash('تم حذف الحجز نهائياً')
    return redirect(url_for('admin.bookings'))

# --- Reports ---
@bp.route('/reports')
def reports():
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    
    # Get query parameters
    from_date_str = request.args.get('from_date', '')
    to_date_str = request.args.get('to_date', '')
    city_id = request.args.get('city_id', type=int)
    
    # Set default date range (last 30 days if not specified)
    if not from_date_str:
        from_date = (datetime.now() - timedelta(days=30)).date()
    else:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    
    if not to_date_str:
        to_date = datetime.now().date()
    else:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    
    # Base queries with date filter
    bookings_query = Booking.query.join(Neighborhood).filter(
        Booking.date >= from_date,
        Booking.date <= to_date
    )
    
    completed_bookings_query = Booking.query.join(Neighborhood).filter(
        Booking.date >= from_date,
        Booking.date <= to_date,
        Booking.status == 'completed'
    )
    
    # Filter by city if specified
    if city_id:
        bookings_query = bookings_query.filter(Neighborhood.city_id == city_id)
        completed_bookings_query = completed_bookings_query.filter(Neighborhood.city_id == city_id)
    
    customers_query = User.query.filter_by(role='customer')
    
    subscriptions_query = Subscription.query.filter(
        Subscription.start_date >= from_date,
        Subscription.start_date <= to_date,
        Subscription.status == 'active'
    )
    
    # Payment Method Stats
    cash_bookings = Booking.query.join(Neighborhood).filter(
        Booking.date >= from_date,
        Booking.date <= to_date,
        Booking.status == 'completed',
        Booking.payment_method == 'cash'
    )
    
    card_bookings = Booking.query.join(Neighborhood).filter(
        Booking.date >= from_date,
        Booking.date <= to_date,
        Booking.status == 'completed',
        Booking.payment_method == 'card'
    )
    
    if city_id:
        cash_bookings = cash_bookings.filter(Neighborhood.city_id == city_id)
        card_bookings = card_bookings.filter(Neighborhood.city_id == city_id)
        
    cash_count = cash_bookings.count()
    card_count = card_bookings.count()
    
    # Calculate totals for cash/card
    cash_total = 0
    for b in cash_bookings.all():
        price = b.service.price + (b.vehicle_size_price or 0)
        # Add products
        for bp in b.products:
            price += bp.product.price * bp.quantity
        # Apply discount/free wash
        if b.used_free_wash:
            price = 0 # Or just products if free wash only covers service? Assuming free wash covers service only.
            # If free wash covers service, products are still paid?
            # Let's assume free wash makes service 0.
            # Re-calculate products only
            p_total = sum(bp.product.price * bp.quantity for bp in b.products)
            price = p_total
        elif b.discount_code:
            if b.discount_code.discount_type == 'percentage':
                disc = (b.service.price + (b.vehicle_size_price or 0)) * b.discount_code.value / 100
                price -= disc
            else:
                price -= b.discount_code.value
            price = max(0, price)
        
        cash_total += price

    card_total = 0
    for b in card_bookings.all():
        price = b.service.price + (b.vehicle_size_price or 0)
        for bp in b.products:
            price += bp.product.price * bp.quantity
        if b.used_free_wash:
             p_total = sum(bp.product.price * bp.quantity for bp in b.products)
             price = p_total
        elif b.discount_code:
            if b.discount_code.discount_type == 'percentage':
                disc = (b.service.price + (b.vehicle_size_price or 0)) * b.discount_code.value / 100
                price -= disc
            else:
                price -= b.discount_code.value
            price = max(0, price)
        
        card_total += price

    # Filter for supervisor
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        if supervisor_neighborhood_ids:
            bookings_query = bookings_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
            completed_bookings_query = completed_bookings_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
            
            # Filter customers who have bookings in supervisor's area
            # Fix AmbiguousForeignKeysError by specifying join condition
            customers_query = customers_query.join(Booking, User.id == Booking.customer_id).filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids)).distinct()
            
            subscriptions_query = subscriptions_query.filter(Subscription.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            # No scope assigned
            bookings_query = bookings_query.filter_by(id=-1)
            completed_bookings_query = completed_bookings_query.filter_by(id=-1)
            customers_query = customers_query.filter_by(id=-1)
            subscriptions_query = subscriptions_query.filter_by(id=-1)

    total_bookings = bookings_query.count()
    completed_bookings = completed_bookings_query.count()
    total_customers = customers_query.count()
    active_subscriptions = subscriptions_query.count()
    
    # Revenue calculations with accurate pricing
    completed_bookings_list = completed_bookings_query.all()
    
    service_revenue = 0
    product_revenue = 0
    
    for booking in completed_bookings_list:
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
        
        # Add service revenue (including vehicle size price)
        service_revenue += (service_price - discount_amount + (booking.vehicle_size_price or 0))
        
        # Add product revenue
        for bp in booking.products:
            product_revenue += (bp.product.price * bp.quantity)
    
    # Subscription revenue (only active subscriptions created in date range)
    sub_rev_query = db.session.query(func.sum(SubscriptionPackage.price))\
        .join(Subscription)\
        .join(Neighborhood, Subscription.neighborhood_id == Neighborhood.id)\
        .filter(
            Subscription.start_date >= from_date,
            Subscription.start_date <= to_date,
            Subscription.status == 'active'
        )
        
    if city_id:
        sub_rev_query = sub_rev_query.filter(Neighborhood.city_id == city_id)
        
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            sub_rev_query = sub_rev_query.filter(Subscription.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            sub_rev_query = sub_rev_query.filter(Subscription.id == -1)
        
    subscription_revenue = sub_rev_query.scalar() or 0
    
    # Total revenue
    total_revenue = service_revenue + product_revenue + subscription_revenue
    
    # Top services (in date range)
    top_services_query = db.session.query(
        Service.name_ar,
        func.count(Booking.id).label('count')
    ).join(Booking)\
    .join(Neighborhood, Booking.neighborhood_id == Neighborhood.id)\
    .filter(
        Booking.date >= from_date,
        Booking.date <= to_date
    )
    
    if city_id:
        top_services_query = top_services_query.filter(Neighborhood.city_id == city_id)
    
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            top_services_query = top_services_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            top_services_query = top_services_query.filter(Booking.id == -1)
        
    top_services = top_services_query.group_by(Service.id)\
    .order_by(func.count(Booking.id).desc())\
    .limit(5).all()
    
    # Employee performance (in date range)
    from sqlalchemy import case
    employee_stats_query = db.session.query(
        User.username,
        func.count(Booking.id).label('total'),
        func.sum(case((Booking.status == 'completed', 1), else_=0)).label('completed')
    ).join(Booking, User.id == Booking.employee_id)\
    .join(Neighborhood, Booking.neighborhood_id == Neighborhood.id)\
    .filter(
        User.role == 'employee',
        Booking.date >= from_date,
        Booking.date <= to_date
    )
    
    if city_id:
        employee_stats_query = employee_stats_query.filter(Neighborhood.city_id == city_id)
    
    if current_user.role == 'supervisor':
        if supervisor_neighborhood_ids:
            employee_stats_query = employee_stats_query.filter(Booking.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            employee_stats_query = employee_stats_query.filter(Booking.id == -1)
        
    employee_stats = employee_stats_query.group_by(User.id).all()
    
    return render_template('admin/reports.html', 
                           total_bookings=total_bookings,
                           completed_bookings=completed_bookings,
                           total_customers=total_customers,
                           active_subscriptions=active_subscriptions,
                           service_revenue=service_revenue,
                           product_revenue=product_revenue,
                           subscription_revenue=subscription_revenue,
                           total_revenue=total_revenue,
                           top_services=top_services,
                           employee_stats=employee_stats,
                           cash_count=cash_count,
                           cash_total=cash_total,
                           card_count=card_count,
                           card_total=card_total,
                           from_date=from_date.strftime('%Y-%m-%d'),
                           city_id=city_id,
                           to_date=to_date.strftime('%Y-%m-%d'))

# --- Settings (Loyalty, Admin Accounts, Backup) ---
@bp.route('/settings/loyalty', methods=['GET', 'POST'])
def loyalty_settings():
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        threshold = request.form.get('threshold', type=int)
        if threshold and threshold > 0:
            settings.loyalty_points_threshold = threshold
            db.session.commit()
            flash(f'تم تحديث عتبة الولاء إلى {threshold} نقطة')
        else:
            flash('الرجاء إدخال قيمة صحيحة', 'error')
    
    return render_template('admin/loyalty_settings.html', current_threshold=settings.loyalty_points_threshold)

@bp.route('/backup/export-json')
def backup_json():
    import json
    from flask import Response
    
    data = {
        'users': [{'id': u.id, 'username': u.username, 'role': u.role} for u in User.query.all()],
        'bookings': [{'id': b.id, 'status': b.status, 'date': str(b.date)} for b in Booking.query.all()],
    }
    
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=backup.json'}
    )

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    form = SiteSettingsForm()
    settings = SiteSettings.get_settings()
    
    if form.validate_on_submit():
        settings.site_name = form.site_name.data
        settings.primary_color = form.primary_color.data
        settings.accent_color = form.accent_color.data
        settings.whatsapp_number = form.whatsapp_number.data
        settings.facebook_url = form.facebook_url.data
        settings.twitter_url = form.twitter_url.data
        settings.instagram_url = form.instagram_url.data
        settings.tiktok_url = form.tiktok_url.data
        settings.mawthooq_url = form.mawthooq_url.data
        settings.terms_content = form.terms_content.data
        
        if form.logo.data:
            import os
            from werkzeug.utils import secure_filename
            from flask import current_app
            
            file = form.logo.data
            filename = secure_filename(file.filename)
            # Ensure filename is unique or standard
            filename = 'logo.png' # Force standard name for simplicity or keep original
            
            # Save to static/uploads or static/images
            upload_dir = os.path.join(current_app.root_path, 'static', 'images')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            settings.logo_path = f'/static/images/{filename}'
            
        db.session.commit()
        flash('تم تحديث إعدادات الموقع بنجاح', 'success')
        return redirect(url_for('admin.settings'))
        
    elif request.method == 'GET':
        form.site_name.data = settings.site_name
        form.primary_color.data = settings.primary_color
        form.accent_color.data = settings.accent_color
        form.whatsapp_number.data = settings.whatsapp_number
        form.facebook_url.data = settings.facebook_url
        form.twitter_url.data = settings.twitter_url
        form.instagram_url.data = settings.instagram_url
        form.tiktok_url.data = settings.tiktok_url
        form.mawthooq_url.data = settings.mawthooq_url
        form.terms_content.data = settings.terms_content

    return render_template('admin/settings.html', form=form, settings=settings)

@bp.route('/notifications/send', methods=['GET', 'POST'])
@login_required
def send_notification():
    form = NotificationForm()
    # Populate user choices
    users = User.query.filter(User.role == 'customer').all()
    choices = [(0, 'All Customers')] + [(u.id, f"{u.username} ({u.phone})") for u in users]
    form.user_id.choices = choices

    if form.validate_on_submit():
        title = form.title.data
        message = form.message.data
        recipient_id = form.user_id.data

        targets = []
        if recipient_id == 0:
            targets = users
        else:
            targets = [User.query.get(recipient_id)]

        count = 0
        for user in targets:
            if not user: continue
            
            # 1. Create DB Notification
            notif = Notification(user_id=user.id, title=title, message=message)
            db.session.add(notif)
            
            # 2. Send Web Push using the improved notification function
            from app.notifications import send_push_notification
            notification_data = {
                "title": title,
                "body": message,
                "icon": "/static/images/logo.png",
                "badge": "/static/images/logo.png",
                "url": "/notifications"
            }
            send_push_notification(user, notification_data)
            
            count += 1
        
        db.session.commit()
        flash(f'Notification sent to {count} users.', 'success')
        return redirect(url_for('admin.send_notification'))

    return render_template('admin/notifications.html', form=form)


# --- Discount Code Management ---
@bp.route('/discount_codes')
def discount_codes():
    codes = DiscountCode.query.order_by(DiscountCode.created_at.desc() if hasattr(DiscountCode, 'created_at') else DiscountCode.id.desc()).all()
    return render_template('admin/discount_codes.html', discount_codes=codes)

@bp.route('/discount_codes/add', methods=['GET', 'POST'])
def add_discount_code():
    if request.method == 'POST':
        code = request.form.get('code')
        discount_type = request.form.get('discount_type')
        value = float(request.form.get('value'))
        valid_until_str = request.form.get('valid_until')
        usage_limit = request.form.get('usage_limit')
        max_uses_per_customer = request.form.get('max_uses_per_customer')
        
        valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
        
        new_code = DiscountCode(
            code=code,
            discount_type=discount_type,
            value=value,
            valid_until=valid_until,
            usage_limit=int(usage_limit) if usage_limit else None,
            max_uses_per_customer=int(max_uses_per_customer) if max_uses_per_customer else 1
        )
        
        try:
            db.session.add(new_code)
            db.session.commit()
            flash('تم إضافة كود الخصم بنجاح', 'success')
            return redirect(url_for('admin.discount_codes'))
        except:
            db.session.rollback()
            flash('حدث خطأ أثناء إضافة الكود. ربما الكود موجود مسبقاً.', 'error')
            
    return render_template('admin/add_discount_code.html')

@bp.route('/discount_codes/edit/<int:id>', methods=['GET', 'POST'])
def edit_discount_code(id):
    code = DiscountCode.query.get_or_404(id)
    
    if request.method == 'POST':
        code.code = request.form.get('code')
        code.discount_type = request.form.get('discount_type')
        code.value = float(request.form.get('value'))
        valid_until_str = request.form.get('valid_until')
        code.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
        
        usage_limit = request.form.get('usage_limit')
        code.usage_limit = int(usage_limit) if usage_limit else None
        
        max_uses_per_customer = request.form.get('max_uses_per_customer')
        code.max_uses_per_customer = int(max_uses_per_customer) if max_uses_per_customer else 1
        
        code.is_active = 'is_active' in request.form
        
        try:
            db.session.commit()
            flash('تم تحديث كود الخصم بنجاح', 'success')
            return redirect(url_for('admin.discount_codes'))
        except:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث الكود.', 'error')
            
    return render_template('admin/edit_discount_code.html', code=code)

@bp.route('/discount_codes/delete/<int:id>', methods=['POST'])
def delete_discount_code(id):
    code = DiscountCode.query.get_or_404(id)
    db.session.delete(code)
    db.session.commit()
    flash('تم حذف كود الخصم بنجاح', 'success')
    return redirect(url_for('admin.discount_codes'))

@bp.route('/discount_codes/stats/<int:id>')
def discount_code_stats(id):
    code = DiscountCode.query.get_or_404(id)
    bookings = Booking.query.filter_by(discount_code_id=id).all()
    total_savings = sum(b.service.price * (code.value / 100) if code.discount_type == 'percentage' else code.value for b in bookings if b.service)
    
    return render_template('admin/discount_code_stats.html', code=code, bookings=bookings, total_savings=total_savings)

# --- Admin Management ---
@bp.route('/admins')
def admins():
    admins = User.query.filter_by(role='admin').all()
    return render_template('admin/admins.html', admins=admins)

@bp.route('/admins/add', methods=['GET', 'POST'])
def add_admin():
    form = AdminUserForm()
    if form.validate_on_submit():
        # Check if username or email exists
        if User.query.filter_by(username=form.username.data).first():
            flash('اسم المستخدم موجود مسبقاً', 'error')
            return render_template('admin/admin_form.html', form=form, title='إضافة مسؤول')
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='admin'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم إضافة المسؤول بنجاح', 'success')
        return redirect(url_for('admin.admins'))
    return render_template('admin/admin_form.html', form=form, title='إضافة مسؤول')

@bp.route('/admins/edit/<int:id>', methods=['GET', 'POST'])
def edit_admin(id):
    admin = User.query.get_or_404(id)
    form = AdminUserForm(obj=admin)
    if form.validate_on_submit():
        admin.username = form.username.data
        admin.email = form.email.data
        if form.password.data:
            admin.set_password(form.password.data)
        db.session.commit()
        flash('تم تعديل بيانات المسؤول', 'success')
        return redirect(url_for('admin.admins'))
    return render_template('admin/admin_form.html', form=form, title='تعديل مسؤول', admin=admin)

@bp.route('/admins/delete/<int:id>')
def delete_admin(id):
    if id == current_user.id:
        flash('لا يمكنك حذف حسابك الحالي', 'error')
        return redirect(url_for('admin.admins'))
        
    admin = User.query.get_or_404(id)
    db.session.delete(admin)
    db.session.commit()
    flash('تم حذف المسؤول', 'success')
    return redirect(url_for('admin.admins'))


# ===== Gift Orders Management =====

@bp.route('/gift-orders')
def gift_orders():
    """List all gift orders with tabs for status"""
    from app.models import GiftOrder
    
    status_filter = request.args.get('status', 'pending')
    
    # Get base query
    base_query = GiftOrder.query
    
    # Filter for supervisors - only show gifts for their neighborhoods
    if current_user.role == 'supervisor':
        supervisor_neighborhood_ids = []
        if current_user.supervisor_neighborhoods:
            supervisor_neighborhood_ids.extend([n.id for n in current_user.supervisor_neighborhoods])
        
        if current_user.supervisor_cities:
            for city in current_user.supervisor_cities:
                supervisor_neighborhood_ids.extend([n.id for n in city.neighborhoods])
        
        if supervisor_neighborhood_ids:
            base_query = base_query.filter(GiftOrder.neighborhood_id.in_(supervisor_neighborhood_ids))
        else:
            base_query = base_query.filter_by(id=-1)  # Empty result
    
    pending_orders = base_query.filter_by(status='pending').order_by(GiftOrder.created_at.desc()).all()
    accepted_orders = base_query.filter_by(status='accepted').order_by(GiftOrder.created_at.desc()).all()
    rejected_orders = base_query.filter_by(status='rejected').order_by(GiftOrder.created_at.desc()).all()
    
    return render_template('admin/gift_orders.html',
                         pending_orders=pending_orders,
                         accepted_orders=accepted_orders,
                         rejected_orders=rejected_orders,
                         status_filter=status_filter)


@bp.route('/gift-orders/<int:id>/accept')
def accept_gift_order(id):
    """Accept a gift order"""
    from app.models import GiftOrder
    
    gift_order = GiftOrder.query.get_or_404(id)
    gift_order.status = 'accepted'
    db.session.commit()
    
    flash('تم قبول طلب الهدية', 'success')
    return redirect(url_for('admin.gift_orders'))


@bp.route('/gift-orders/<int:id>/reject')
def reject_gift_order(id):
    """Reject a gift order"""
    from app.models import GiftOrder
    
    gift_order = GiftOrder.query.get_or_404(id)
    gift_order.status = 'rejected'
    db.session.commit()
    
    flash('تم رفض طلب الهدية', 'warning')
    return redirect(url_for('admin.gift_orders'))

