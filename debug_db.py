from app import create_app, db
from app.models import User, Booking

app = create_app()

with app.app_context():
    # Find the customer
    customer = User.query.filter_by(username='customer').first()
    if not customer:
        print("Customer 'customer' not found!")
        users = User.query.all()
        print(f"Available users: {[u.username for u in users]}")
    else:
        print(f"Checking bookings for user: {customer.username} (ID: {customer.id})")
        bookings = Booking.query.filter_by(customer_id=customer.id).all()
        print(f"Total bookings found: {len(bookings)}")
        
        print("-" * 80)
        print(f"{'ID':<5} | {'Date':<12} | {'Status':<15} | {'Rating':<10} | {'Is None?'}")
        print("-" * 80)
        
        for b in bookings:
            rating_val = b.rating
            is_none = (rating_val is None)
            print(f"{b.id:<5} | {b.date} | {b.status:<15} | {str(rating_val):<10} | {is_none}")
            
        # Test the query exactly as in routes.py
        unrated = Booking.query.filter(
            Booking.customer_id == customer.id, 
            Booking.status == 'completed', 
            (Booking.rating == None) | (Booking.rating == 0)
        ).order_by(Booking.date.desc(), Booking.time.desc()).first()
        
        print("-" * 80)
        if unrated:
            print(f"Query FOUND unrated booking: {unrated.id}")
        else:
            print("Query returned NONE for unrated booking.")
