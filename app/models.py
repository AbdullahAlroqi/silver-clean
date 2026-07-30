from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association table for Employee-Neighborhood many-to-many
employee_neighborhoods = db.Table('employee_neighborhoods',
    db.Column('employee_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('neighborhood_id', db.Integer, db.ForeignKey('neighborhood.id'), primary_key=True)
)

# Association table for Supervisor-City many-to-many
supervisor_cities = db.Table('supervisor_cities',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('city_id', db.Integer, db.ForeignKey('city.id'), primary_key=True)
)

# Association table for Supervisor-Neighborhood many-to-many
supervisor_neighborhoods = db.Table('supervisor_neighborhoods',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('neighborhood_id', db.Integer, db.ForeignKey('neighborhood.id'), primary_key=True)
)

warehouse_cities = db.Table('warehouse_cities',
    db.Column('warehouse_id', db.Integer, db.ForeignKey('warehouse.id'), primary_key=True),
    db.Column('city_id', db.Integer, db.ForeignKey('city.id'), primary_key=True)
)

warehouse_neighborhoods = db.Table('warehouse_neighborhoods',
    db.Column('warehouse_id', db.Integer, db.ForeignKey('warehouse.id'), primary_key=True),
    db.Column('neighborhood_id', db.Integer, db.ForeignKey('neighborhood.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20)) # 'admin', 'employee', 'customer', 'supervisor'
    points = db.Column(db.Integer, default=0)
    free_washes = db.Column(db.Integer, default=0)
    push_subscription = db.Column(db.Text) # JSON string for Web Push subscription
    reset_code = db.Column(db.String(6), nullable=True)
    reset_code_expiration = db.Column(db.DateTime, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(255), nullable=True)
    is_on_break = db.Column(db.Boolean, default=False)
    break_type = db.Column(db.String(20), nullable=True)  # full_day, date, time
    break_date = db.Column(db.Date, nullable=True)
    break_start_time = db.Column(db.Time, nullable=True)
    break_end_time = db.Column(db.Time, nullable=True)
    
    # Referral System
    referral_code = db.Column(db.String(10), unique=True, index=True)  # e.g. SILVC4821
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who referred this user
    used_influencer_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=True)  # Used an influencer code at signup
    
    # Relationships
    vehicles = db.relationship('Vehicle', backref='owner', lazy='dynamic')
    bookings = db.relationship('Booking', backref='customer', foreign_keys='Booking.customer_id', lazy='dynamic')
    assigned_bookings = db.relationship('Booking', backref='employee', foreign_keys='Booking.employee_id', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='customer', foreign_keys='Subscription.customer_id', lazy='dynamic')
    assigned_subscriptions = db.relationship('Subscription', backref='assigned_employee', foreign_keys='Subscription.employee_id', lazy='dynamic')
    neighborhoods = db.relationship('Neighborhood', secondary=employee_neighborhoods, backref=db.backref('employees', lazy='dynamic'))
    schedules = db.relationship('EmployeeSchedule', backref='employee', lazy='dynamic')
    
    # Referral relationships
    referrals_made = db.relationship('ReferralRecord', foreign_keys='ReferralRecord.referrer_id', backref='referrer', lazy='dynamic')
    referral_record = db.relationship('ReferralRecord', foreign_keys='ReferralRecord.referred_user_id', backref='referred_user', uselist=False)
    
    # Supervisor Relationships
    supervisor_cities = db.relationship('City', secondary=supervisor_cities, backref=db.backref('supervisors', lazy='dynamic'))
    supervisor_neighborhoods = db.relationship('Neighborhood', secondary=supervisor_neighborhoods, backref=db.backref('supervisors', lazy='dynamic'))

    def add_loyalty_point(self):
        """Add a loyalty point and check for free wash reward using system threshold"""
        settings = SiteSettings.get_settings()
        threshold = settings.loyalty_points_threshold or 10
        
        self.points = (self.points or 0) + 1
        if self.points >= threshold:
            self.points = 0
            self.free_washes = (self.free_washes or 0) + 1
            return True # Reward granted (Free wash added)
        return False

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    @staticmethod
    def generate_referral_code():
        """Generate a unique referral code in format SILVC + 4 digits (+ optional letter)"""
        import random
        import string
        while True:
            digits = ''.join(random.choices(string.digits, k=4))
            # 50% chance of adding a trailing letter for variety
            suffix = random.choice(string.ascii_uppercase) if random.random() > 0.5 else ''
            code = f'SILVC{digits}{suffix}'
            # Check uniqueness
            if not User.query.filter_by(referral_code=code).first():
                return code

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class VehicleSize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price_adjustment = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    vehicles = db.relationship('Vehicle', backref='size', lazy='dynamic')



class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    vehicle_size_id = db.Column(db.Integer, db.ForeignKey('vehicle_size.id'), nullable=True)
    brand = db.Column(db.String(64))
    plate_number = db.Column(db.String(20))

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    osm_place_id = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    neighborhoods = db.relationship('Neighborhood', backref='city', lazy='dynamic')
    # Price overrides (relationships defined in the respective classes)

class Neighborhood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    osm_name = db.Column(db.String(200), nullable=True)
    boundary_coords = db.Column(db.Text, nullable=True)  # GeoJSON polygon
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def contains_point(self, lat, lng):
        """Check if a given (lat, lng) point is inside the neighborhood's boundary using Ray-Casting."""
        if not self.boundary_coords:
            return True  # If no boundary is defined, assume it's valid
        
        import json
        try:
            geometry = json.loads(self.boundary_coords)
            
            # GeoJSON format for Polygon: { "type": "Polygon", "coordinates": [ [ring0], [hole1], ... ] }
            if geometry.get('type') == 'Polygon':
                return self._is_in_poly_with_holes(lng, lat, geometry.get('coordinates', []))
                
            elif geometry.get('type') == 'MultiPolygon':
                for polygon_coords in geometry.get('coordinates', []):
                    if self._is_in_poly_with_holes(lng, lat, polygon_coords):
                        return True
                return False
        except (json.JSONDecodeError, IndexError, TypeError):
            pass
            
        return True # Fallback

    def _is_in_poly_with_holes(self, x, y, rings):
        """Check if point is in exterior ring and NOT in any interior holes."""
        if not rings:
            return False
        # Point must be inside the first ring (exterior)
        if not self._point_in_ring(x, y, rings[0]):
            return False
        # And NOT inside any subsequent rings (holes)
        for hole in rings[1:]:
            if self._point_in_ring(x, y, hole):
                return False
        return True

    def _point_in_ring(self, x, y, ring):
        """Ray-casting algorithm for a single ring."""
        inside = False
        n = len(ring)
        if n < 3: return False
        p1x, p1y = ring[0]
        for i in range(1, n + 1):
            p2x, p2y = ring[i % n]
            if ((p1y > y) != (p2y > y)) and (x < (p2x - p1x) * (y - p1y) / (p2y - p1y) + p1x):
                inside = not inside
            p1x, p1y = p2x, p2y
        return inside

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    duration = db.Column(db.Integer) # in minutes
    description = db.Column(db.String(255))
    includes_free_wash = db.Column(db.Boolean, default=True)
    awards_loyalty_point = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    # city_prices relationship defined in CityServicePrice

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    image_url = db.Column(db.String(255))
    stock_quantity = db.Column(db.Integer, default=0)  # Global stock (fallback)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship to location-based stock
    location_stocks = db.relationship('ProductStock', backref='product', lazy='dynamic')
    # city_prices relationship defined in CityProductPrice

class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    cities = db.relationship('City', secondary=warehouse_cities, backref=db.backref('warehouses', lazy='dynamic'))
    neighborhoods = db.relationship('Neighborhood', secondary=warehouse_neighborhoods, backref=db.backref('warehouses', lazy='dynamic'))
    product_stocks = db.relationship('ProductStock', backref='warehouse', lazy='dynamic')

class ProductStock(db.Model):
    """Product stock per warehouse or legacy city/neighborhood"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=True)
    
    # Relationships
    city = db.relationship('City')
    neighborhood = db.relationship('Neighborhood')
    
    # Unique constraint: one record per product per location
    __table_args__ = (
        db.UniqueConstraint('product_id', 'city_id', 'neighborhood_id', name='unique_product_location'),
    )

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    date = db.Column(db.Date)
    time = db.Column(db.Time)
    status = db.Column(db.String(20), default='pending') # pending, assigned, en_route, arrived, in_progress, completed, cancelled
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    total_price = db.Column(db.Float, default=0.0)
    is_multi_vehicle = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Rating fields
    rating = db.Column(db.Integer, nullable=True)
    rating_comment = db.Column(db.Text, nullable=True)
    rating_date = db.Column(db.DateTime, nullable=True)

    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)  # For subscription wash bookings
    used_free_wash = db.Column(db.Boolean, default=False)
    vehicle_size_price = db.Column(db.Float, default=0.0) # Store price adjustment at time of booking
    custom_service_price = db.Column(db.Float, nullable=True) # Override base service price
    payment_method = db.Column(db.String(20), default='cash') # 'cash' or 'card'
    
    # Timer fields for tracking service duration
    started_at = db.Column(db.DateTime, nullable=True)      # Set when status → in_progress
    completed_at = db.Column(db.DateTime, nullable=True)    # Set when status → completed
    cancelled_at = db.Column(db.DateTime, nullable=True)    # Set when status → cancelled
    
    # Cancellation reason from customer
    cancellation_reason = db.Column(db.Text, nullable=True)

    @property
    def total_duration(self):
        """Calculate total duration of all items in this booking"""
        total = 0
        for item in self.items:
            quantity = item.quantity or 1
            if item.service and item.service.duration:
                total += item.service.duration * quantity
            else:
                total += 60 * quantity # Default duration
        return total if total > 0 else (self.service.duration if self.service and self.service.duration else 60)

    # Relationships
    items = db.relationship('BookingItem', backref='booking', lazy='dynamic', cascade='all, delete-orphan')
    neighborhood = db.relationship('Neighborhood')
    products = db.relationship('BookingProduct', backref='booking', lazy='dynamic', cascade='all, delete-orphan')
    discount_code = db.relationship('DiscountCode')
    subscription = db.relationship('Subscription', backref='wash_bookings')
    vehicle = db.relationship('Vehicle', foreign_keys=[vehicle_id])
    service = db.relationship('Service', foreign_keys=[service_id])

class BookingItem(db.Model):
    """Individual vehicle and service item within a booking"""
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    # Snapshot of prices at time of booking
    service_price = db.Column(db.Float, default=0.0)
    size_price_adjustment = db.Column(db.Float, default=0.0)
    total_item_price = db.Column(db.Float, default=0.0)
    
    # Relationships
    vehicle = db.relationship('Vehicle')
    service = db.relationship('Service')

# ... (BookingProduct class)

class BookingProduct(db.Model):
    """Association table for Booking-Product many-to-many with quantity"""
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=True) # Store price at time of booking or override
    
    # Relationship
    product = db.relationship('Product')

class DiscountCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_type = db.Column('type', db.String(20), nullable=False)  # 'percentage' or 'fixed'
    value = db.Column(db.Float, nullable=False)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=False)
    usage_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column('usage_count', db.Integer, default=0)
    max_uses_per_customer = db.Column(db.Integer, nullable=True, default=1)  # الحد الأقصى للاستخدام لكل عميل
    is_active = db.Column('active', db.Boolean, default=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True, index=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    assigned_customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    city = db.relationship('City', foreign_keys=[city_id])
    neighborhood = db.relationship('Neighborhood', foreign_keys=[neighborhood_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assigned_customer = db.relationship('User', foreign_keys=[assigned_customer_id])
    
    # Influencer specifics
    is_influencer = db.Column(db.Boolean, default=False)
    influencer_name = db.Column(db.String(100), nullable=True)

    def applies_to(self, neighborhood):
        """Return whether this code can be used in the selected booking location."""
        if not neighborhood:
            return self.city_id is None and self.neighborhood_id is None
        if self.neighborhood_id is not None:
            return self.neighborhood_id == neighborhood.id
        if self.city_id is not None:
            return self.city_id == neighborhood.city_id
        return True

    def is_available_to(self, customer):
        """A recovery code may only be used by the customer it was issued to."""
        return self.assigned_customer_id is None or (
            customer is not None and self.assigned_customer_id == customer.id
        )

    @property
    def scope_label(self):
        if self.neighborhood:
            city_name = self.neighborhood.city.name_ar if self.neighborhood.city else ''
            return f'{city_name} - {self.neighborhood.name_ar}'.strip(' -')
        if self.city:
            return self.city.name_ar
        return None

class Season(db.Model):
    """Seasonal periods where custom prices apply (e.g., Eid, National Day)"""
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    allow_free_washes = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    service_prices = db.relationship('SeasonalServicePrice', backref='season', lazy='dynamic', cascade='all, delete-orphan')
    product_prices = db.relationship('SeasonalProductPrice', backref='season', lazy='dynamic', cascade='all, delete-orphan')

class SeasonalServicePrice(db.Model):
    """Override price for a service during a specific season"""
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relationship
    service = db.relationship('Service')
    
    __table_args__ = (
        db.UniqueConstraint('season_id', 'service_id', name='unique_season_service'),
    )

class SeasonalProductPrice(db.Model):
    """Override price for a product during a specific season"""
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relationship
    product = db.relationship('Product')
    
    __table_args__ = (
        db.UniqueConstraint('season_id', 'product_id', name='unique_season_product'),
    )

class SubscriptionPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    wash_count = db.Column(db.Integer)
    duration_days = db.Column(db.Integer)
    description = db.Column(db.String(255))
    package_type = db.Column(db.String(20), default='subscription')  # subscription, polishing
    is_active = db.Column(db.Boolean, default=True)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('subscription_package.id'), nullable=True)
    plan_type = db.Column(db.String(64)) # Keep for legacy or ad-hoc
    remaining_washes = db.Column(db.Integer, default=0)
    preferred_time = db.Column(db.String(20), nullable=True)  # 'morning', 'afternoon', 'evening', 'flexible'
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'rejected', 'expired'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with foreign_keys specified
    package = db.relationship('SubscriptionPackage')
    neighborhood = db.relationship('Neighborhood')
    vehicle = db.relationship('Vehicle')

class PolishingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('subscription_package.id'), nullable=True)
    preferred_time = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, completed, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship('User', backref=db.backref('polishing_orders', lazy='dynamic'))
    vehicle = db.relationship('Vehicle')
    neighborhood = db.relationship('Neighborhood')
    package = db.relationship('SubscriptionPackage')


class CheckoutSession(db.Model):
    """Tracks an authenticated customer's unfinished checkout journey."""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    flow_type = db.Column(db.String(30), nullable=False, index=True)
    page_name = db.Column(db.String(100), nullable=False)
    step_name = db.Column(db.String(100), nullable=True)
    form_data = db.Column(db.Text, nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True, index=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True, index=True)
    recovery_discount_code_id = db.Column(
        db.Integer, db.ForeignKey('discount_code.id'), nullable=True, index=True
    )
    estimated_total = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship('User', foreign_keys=[customer_id])
    city = db.relationship('City', foreign_keys=[city_id])
    neighborhood = db.relationship('Neighborhood', foreign_keys=[neighborhood_id])
    recovery_discount_code = db.relationship(
        'DiscountCode', foreign_keys=[recovery_discount_code_id]
    )


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(64))
    message = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmployeeSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday
    shift_number = db.Column(db.Integer, default=1)  # 1=first shift, 2=second shift
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_active = db.Column(db.Boolean, default=True)

class SiteSettings(db.Model):
    """Singleton model for site-wide settings"""
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), default='Silver Clean')
    logo_path = db.Column(db.String(200), default='/static/images/logo.png')
    primary_color = db.Column(db.String(7), default='#1E40AF')  # Blue
    accent_color = db.Column(db.String(7), default='#3B82F6')   # Light Blue
    whatsapp_number = db.Column(db.String(20), default='')
    facebook_url = db.Column(db.String(200), default='')
    twitter_url = db.Column(db.String(200), default='')
    instagram_url = db.Column(db.String(200), default='')
    tiktok_url = db.Column(db.String(200), default='')
    mawthooq_url = db.Column(db.String(200), default='')
    terms_content = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    loyalty_points_threshold = db.Column(db.Integer, default=10)
    booking_days_limit = db.Column(db.Integer, default=7)       # عدد أيام حجز الخدمة (0 = إيقاف)
    subscription_days_limit = db.Column(db.Integer, default=7)   # عدد أيام حجز الاشتراك (0 = إيقاف)
    referral_target_count = db.Column(db.Integer, default=10)    # عدد الإحالات المطلوبة للحصول على غسلة مجانية
    maintenance_mode = db.Column(db.Boolean, default=False)      # إيقاف الموقع مؤقتاً للصيانة
    
    @staticmethod
    def get_settings():
        """Get or create singleton settings instance"""
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings(site_name='Silver Clean')
            db.session.add(settings)
            db.session.commit()
        return settings

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy=True, cascade="all, delete-orphan"))



class GiftOrder(db.Model):
    """Gift order for gifting a wash or subscription to someone"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # المهدي
    recipient_name = db.Column(db.String(100))  # اسم المهدى له
    recipient_phone = db.Column(db.String(20))  # رقم جوال المهدى له (+966...)
    
    # Recipient location for gift delivery
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    
    gift_type = db.Column(db.String(20))  # 'wash' or 'subscription'
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('subscription_package.id'), nullable=True)
    
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref='gift_orders')
    service = db.relationship('Service')
    package = db.relationship('SubscriptionPackage')
    city = db.relationship('City')
    neighborhood = db.relationship('Neighborhood')

class GiftOrderProduct(db.Model):
    """Products included in a gift order"""
    id = db.Column(db.Integer, primary_key=True)
    gift_order_id = db.Column(db.Integer, db.ForeignKey('gift_order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    
    # Relationships
    gift_order = db.relationship('GiftOrder', backref='products')
    product = db.relationship('Product')


class Announcement(db.Model):
    """Announcements displayed in the customer home page carousel"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(255))
    link_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmployeeLocation(db.Model):
    """Real-time employee location tracking"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=True)  # GPS accuracy in meters
    is_tracking = db.Column(db.Boolean, default=True)  # Is employee actively tracking
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = db.relationship('User', backref=db.backref('location', uselist=False, cascade="all, delete-orphan"))


class CityServicePrice(db.Model):
    """City and size specific price override for a service"""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    vehicle_size_id = db.Column(db.Integer, db.ForeignKey('vehicle_size.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    city = db.relationship('City', backref=db.backref('city_service_prices', lazy='dynamic', cascade='all, delete-orphan'))
    service = db.relationship('Service', backref=db.backref('city_size_prices', lazy='dynamic', cascade='all, delete-orphan'))
    size = db.relationship('VehicleSize', backref=db.backref('city_service_prices_list', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('city_id', 'service_id', 'vehicle_size_id', name='unique_city_service_size'),
    )


class CityProductPrice(db.Model):
    """City-specific price override for a product"""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    city = db.relationship('City', backref=db.backref('city_product_prices', lazy='dynamic', cascade='all, delete-orphan'))
    product = db.relationship('Product', backref=db.backref('city_prices_list', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('city_id', 'product_id', name='unique_city_product'),
    )


class CityPackagePrice(db.Model):
    """City-specific price override for a subscription package"""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('subscription_package.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    city = db.relationship('City', backref=db.backref('city_package_prices', lazy='dynamic', cascade='all, delete-orphan'))
    package = db.relationship('SubscriptionPackage', backref=db.backref('city_prices_list', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('city_id', 'package_id', name='unique_city_package'),
    )


class ReferralRecord(db.Model):
    """Tracks each referral: who referred whom and first wash status"""
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    name_prefix = db.Column(db.String(3))  # First 3 letters of referred user's name
    first_wash_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



