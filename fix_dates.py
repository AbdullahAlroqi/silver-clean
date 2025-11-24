from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Fixing invalid date values...\n")
    
    # Fix DiscountCode.valid_from
    print("1. Fixing DiscountCode.valid_from...")
    result = db.session.execute(text("SELECT id, valid_from FROM discount_code WHERE typeof(valid_from) != 'text'"))
    rows = result.fetchall()
    for row in rows:
        print(f"  Fixing ID {row[0]}: {row[1]} -> {row[1]}-01-01 00:00:00")
        db.session.execute(text(f"UPDATE discount_code SET valid_from = '{row[1]}-01-01 00:00:00' WHERE id = {row[0]}"))
    db.session.commit()
    
    # Fix Subscription.created_at NULL values
    print("\n2. Fixing Subscription.created_at NULL values...")
    result = db.session.execute(text("SELECT id FROM subscription WHERE created_at IS NULL"))
    rows = result.fetchall()
    for row in rows:
        print(f"  Fixing ID {row[0]}: NULL -> 2024-01-01 00:00:00")
        db.session.execute(text(f"UPDATE subscription SET created_at = '2024-01-01 00:00:00' WHERE id = {row[0]}"))
    db.session.commit()
    
    print("\nDone! All date values fixed.")
