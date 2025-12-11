from app import create_app, db
from app.models import User, Neighborhood, Service
from flask_login import login_user
from datetime import date, timedelta

app = create_app()

with app.test_request_context():
    # Find a customer
    customer = User.query.filter_by(role='customer').first()
    if not customer:
        print("No customer found!")
        # Create one
        customer = User(username='test_cust', email='test@test.com', role='customer')
        customer.set_password('password')
        db.session.add(customer)
        db.session.commit()
        print("Created test customer")

    print(f"Testing as user: {customer.username} (Role: {customer.role})")

    # Find neighborhood and service
    n = Neighborhood.query.first()
    s = Service.query.first()
    
    if not n or not s:
        print("Missing neighborhood or service")
        exit()
        
    print(f"Neighborhood: {n.name_ar} (ID: {n.id})")
    print(f"Service: {s.name_ar} (ID: {s.id})")

    with app.test_client() as client:
        # Login
        with client.session_transaction() as sess:
            from flask_login import login_user
            # We can't easily use login_user with test_client without a request context or mocking
            # But we can simulate the session
            sess['_user_id'] = str(customer.id)
            sess['_fresh'] = True

        # Test API
        tomorrow = date.today() + timedelta(days=1)
        date_str = tomorrow.strftime('%Y-%m-%d')
        
        print(f"Requesting slots for {date_str}...")
        response = client.get(f'/customer/api/available-times?date={date_str}&neighborhood_id={n.id}&service_id={s.id}')
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Data: {response.get_json()}")
        else:
            print(f"Response: {response.data}")
