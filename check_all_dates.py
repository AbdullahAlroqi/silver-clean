from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== Checking ALL date/datetime columns ===\n")
    
    # Check DiscountCode
    print("1. DiscountCode.valid_from and valid_until...")
    result = db.session.execute(text("SELECT id, valid_from, valid_until FROM discount_code"))
    for row in result.fetchall():
        print(f"  ID {row[0]}: valid_from={row[1]} (type: {type(row[1])}), valid_until={row[2]} (type: {type(row[2])})")
    
    # Check Booking dates
    print("\n2. Booking.date, time, created_at...")
    result = db.session.execute(text("SELECT id, date, time, created_at FROM booking LIMIT 5"))
    for row in result.fetchall():
        print(f"  ID {row[0]}: date={row[1]} ({type(row[1])}), time={row[2]} ({type(row[2])}), created_at={row[3]} ({type(row[3])})")
    
    # Check Subscription dates
    print("\n3. Subscription.start_date, end_date, created_at...")
    result = db.session.execute(text("SELECT id, start_date, end_date, created_at FROM subscription"))
    for row in result.fetchall():
        print(f"  ID {row[0]}: start_date={row[1]} ({type(row[1])}), end_date={row[2]} ({type(row[2])}), created_at={row[3]} ({type(row[3])})")
    
    # Check for any NULL or weird values
    print("\n4. Checking for NULL or invalid values...")
    
    # Subscription start_date
    result = db.session.execute(text("SELECT COUNT(*) FROM subscription WHERE start_date IS NULL"))
    count = result.scalar()
    if count > 0:
        print(f"  WARNING: {count} subscriptions with NULL start_date!")
    
    # Subscription end_date
    result = db.session.execute(text("SELECT COUNT(*) FROM subscription WHERE end_date IS NULL"))
    count = result.scalar()
    if count > 0:
        print(f"  WARNING: {count} subscriptions with NULL end_date!")
        
    print("\n=== Done ===")
