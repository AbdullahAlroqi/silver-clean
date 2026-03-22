from app import create_app, db
from app.models import Booking

app = create_app()
with app.app_context():
    bookings = Booking.query.filter(Booking.location_lat == None).all()
    count = 0
    for b in bookings:
        b.location_lat = 24.7136
        b.location_lng = 46.6753
        count += 1
    db.session.commit()
    print(f"Updated {count} bookings with dummy coordinates.")
