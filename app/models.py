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
    
    # Relationships
    vehicles = db.relationship('Vehicle', backref='owner', lazy='dynamic')
    bookings = db.relationship('Booking', backref='customer', foreign_keys='Booking.customer_id', lazy='dynamic')
    assigned_bookings = db.relationship('Booking', backref='employee', foreign_keys='Booking.employee_id', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='customer', foreign_keys='Subscription.customer_id', lazy='dynamic')
    assigned_subscriptions = db.relationship('Subscription', backref='assigned_employee', foreign_keys='Subscription.employee_id', lazy='dynamic')
    neighborhoods = db.relationship('Neighborhood', secondary=employee_neighborhoods, backref=db.backref('employees', lazy='dynamic'))
    schedules = db.relationship('EmployeeSchedule', backref='employee', lazy='dynamic')
    
    # Supervisor Relationships
    supervisor_cities = db.relationship('City', secondary=supervisor_cities, backref=db.backref('supervisors', lazy='dynamic'))
    supervisor_neighborhoods = db.relationship('Neighborhood', secondary=supervisor_neighborhoods, backref=db.backref('supervisors', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

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
    is_active = db.Column(db.Boolean, default=True)
    neighborhoods = db.relationship('Neighborhood', backref='city', lazy='dynamic')

class Neighborhood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    duration = db.Column(db.Integer) # in minutes
    description = db.Column(db.String(255))
    includes_free_wash = db.Column(db.Boolean, default=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    image_url = db.Column(db.String(255))
    stock_quantity = db.Column(db.Integer, default=0)  # Global stock (fallback)
    
    # Relationship to location-based stock
    location_stocks = db.relationship('ProductStock', backref='product', lazy='dynamic')

class ProductStock(db.Model):
    """Product stock per city/neighborhood"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey('neighborhood.id'), nullable=True)
    quantity = db.Column(db.Integer, default=0)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Rating fields
    rating = db.Column(db.Integer, nullable=True)
    rating_comment = db.Column(db.Text, nullable=True)
    rating_date = db.Column(db.DateTime, nullable=True)

    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)  # For subscription wash bookings
    used_free_wash = db.Column(db.Boolean, default=False)
    vehicle_size_price = db.Column(db.Float, default=0.0) # Store price adjustment at time of booking
    payment_method = db.Column(db.String(20), default='cash') # 'cash' or 'card'
    
    # Relationships
    vehicle = db.relationship('Vehicle')
    service = db.relationship('Service')
    neighborhood = db.relationship('Neighborhood')
    products = db.relationship('BookingProduct', backref='booking', lazy='dynamic')
    discount_code = db.relationship('DiscountCode')
    subscription = db.relationship('Subscription', backref='wash_bookings')  # Link to subscription

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

class SubscriptionPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(64))
    name_en = db.Column(db.String(64))
    price = db.Column(db.Float)
    wash_count = db.Column(db.Integer)
    duration_days = db.Column(db.Integer)
    description = db.Column(db.String(255))
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

class BookingProduct(db.Model):
    """Association table for Booking-Product many-to-many with quantity"""
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    
    # Relationship
    product = db.relationship('Product')

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
    
    employee = db.relationship('User', backref=db.backref('location', uselist=False))
