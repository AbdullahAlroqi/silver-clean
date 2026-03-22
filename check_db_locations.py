from app import create_app, db
from app.models import Booking

app = create_app()
with app.app_context():
    bookings = Booking.query.order_by(Booking.id.desc()).limit(5).all()
    for b in bookings:
        print(f"Booking {b.id}: lat={b.location_lat}, lng={b.location_lng}")
