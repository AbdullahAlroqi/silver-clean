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
