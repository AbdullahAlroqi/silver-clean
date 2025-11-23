from app import create_app, db
from app.models import User, City, Neighborhood, Service, SubscriptionPackage, EmployeeSchedule
from werkzeug.security import generate_password_hash

app = create_app()

def seed_data():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        # Check if data exists
        if User.query.first():
            print("Data already exists. Skipping seed.")
            return

        print("Seeding data...")

        # 1. Users
        admin = User(username='admin', email='admin@silverclean.com', role='admin', phone='0500000000')
        admin.set_password('admin123')

        employee = User(username='employee', email='employee@silverclean.com', role='employee', phone='0500000001')
        employee.set_password('employee123')

        customer = User(username='customer', email='customer@silverclean.com', role='customer', phone='0500000002')
        customer.set_password('customer123')
        customer.points = 5 # Give some initial points

        db.session.add_all([admin, employee, customer])

        # 2. Locations
        riyadh = City(name_ar='الرياض', name_en='Riyadh', is_active=True)
        jeddah = City(name_ar='جدة', name_en='Jeddah', is_active=True)
        dammam = City(name_ar='الدمام', name_en='Dammam', is_active=True)

        db.session.add_all([riyadh, jeddah, dammam])
        db.session.commit() # Commit to get IDs

        # Neighborhoods
        neighborhoods = [
            Neighborhood(name_ar='العليا', name_en='Olaya', city_id=riyadh.id, is_active=True),
            Neighborhood(name_ar='الملقا', name_en='Al Malqa', city_id=riyadh.id, is_active=True),
            Neighborhood(name_ar='النرجس', name_en='Al Narjis', city_id=riyadh.id, is_active=True),
            Neighborhood(name_ar='الروضة', name_en='Al Rawdah', city_id=jeddah.id, is_active=True),
            Neighborhood(name_ar='الشاطئ', name_en='Al Shatea', city_id=jeddah.id, is_active=True),
            Neighborhood(name_ar='الفيصلية', name_en='Al Faisaliyah', city_id=dammam.id, is_active=True),
        ]
        db.session.add_all(neighborhoods)

        # 3. Services
        services = [
            Service(name_ar='غسيل خارجي', name_en='Exterior Wash', price=35.0, duration=30, description='غسيل خارجي للسيارة مع تلميع الإطارات'),
            Service(name_ar='غسيل داخلي وخارجي', name_en='Full Wash', price=60.0, duration=45, description='غسيل شامل للسيارة من الداخل والخارج'),
            Service(name_ar='تلميع ساطع', name_en='Polishing', price=150.0, duration=90, description='تلميع الهيكل الخارجي وإزالة الخدوش السطحية'),
        ]
        db.session.add_all(services)

        # 4. Subscription Packages
        packages = [
            SubscriptionPackage(name_ar='الباقة الفضية', name_en='Silver Package', price=150.0, wash_count=4, duration_days=30, description='4 غسلات خارجية شهرياً', is_active=True),
            SubscriptionPackage(name_ar='الباقة الذهبية', name_en='Gold Package', price=250.0, wash_count=4, duration_days=30, description='4 غسلات شاملة (داخلي وخارجي) شهرياً', is_active=True),
            SubscriptionPackage(name_ar='باقة كبار الشخصيات', name_en='VIP Package', price=500.0, wash_count=8, duration_days=30, description='8 غسلات شاملة + تلميع مرة واحدة', is_active=True),
        ]
        db.session.add_all(packages)
        
        db.session.commit()
        
        # 5. Employee Schedules and Neighborhoods
        from app.models import EmployeeSchedule
        from datetime import time
        
        # Assign employee to neighborhoods (العليا, الملقا)
        employee.neighborhoods.append(neighborhoods[0])  # العليا
        employee.neighborhoods.append(neighborhoods[1])  # الملقا
        
        # Create work schedule (Sunday to Thursday, 8 AM to 8 PM)
        for day in range(6, 7):  # Sunday (6 in Python's weekday)
            schedule = EmployeeSchedule(
                employee_id=employee.id,
                day_of_week=day,
                start_time=time(8, 0),
                end_time=time(20, 0),
                is_active=True
            )
            db.session.add(schedule)
        
        for day in range(0, 4):  # Monday(0) to Thursday(3)
            schedule = EmployeeSchedule(
                employee_id=employee.id,
                day_of_week=day,
                start_time=time(8, 0),
                end_time=time(20, 0),
                is_active=True
            )
            db.session.add(schedule)

        db.session.commit()
        print("Database seeded successfully!")
        print("Admin: admin / admin123")
        print("Employee: employee / employee123")
        print("Customer: customer / customer123")

if __name__ == '__main__':
    seed_data()
