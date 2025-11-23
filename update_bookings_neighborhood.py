"""
Update existing bookings to have neighborhood_id
Run this once: python update_bookings_neighborhood.py
"""
from app import create_app, db
from app.models import Booking

app = create_app()

with app.app_context():
    # Get all bookings without neighborhood_id
    bookings = Booking.query.filter(Booking.neighborhood_id == None).all()
    
    print(f"Found {len(bookings)} bookings without neighborhood_id")
    
    for booking in bookings:
        # Try to get neighborhood from employee
        if booking.employee and booking.employee.neighborhoods:
            # Use the first assigned neighborhood of the employee
            neighborhood = booking.employee.neighborhoods[0]
            booking.neighborhood_id = neighborhood.id
            print(f"Booking #{booking.id}: assigned neighborhood {neighborhood.name_ar}")
        # Fallback: try to get from vehicle's owner
        elif booking.vehicle and booking.vehicle.owner:
            customer = booking.vehicle.owner
            # You might want to add logic here based on customer's location
            # For now, we'll skip these
            print(f"Booking #{booking.id}: skipped (no employee neighborhood)")
    
    db.session.commit()
    print("Update complete!")
