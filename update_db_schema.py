
import sqlite3
import sqlalchemy
from app import create_app, db

app = create_app()

def upgrade():
    print("Starting database schema update...")
    with app.app_context():
        # Get the database URI to determine if we are using SQLite
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        # 1. Add custom_service_price to Booking
        try:
            with db.engine.connect() as conn:
                # distinct connection for explicit transaction handling if needed, 
                # but with SQLAlchemy text() execution it usually autocommits or we strictly commit.
                conn.execute(sqlalchemy.text("ALTER TABLE booking ADD COLUMN custom_service_price FLOAT"))
                conn.commit()
                print("SUCCESS: Added custom_service_price to booking")
        except Exception as e:
            print(f"INFO: Could not add custom_service_price (probably exists): {e}")

        # 2. Add unit_price to BookingProduct
        try:
             with db.engine.connect() as conn:
                conn.execute(sqlalchemy.text("ALTER TABLE booking_product ADD COLUMN unit_price FLOAT"))
                conn.commit()
                print("SUCCESS: Added unit_price to booking_product")
        except Exception as e:
            print(f"INFO: Could not add unit_price (probably exists): {e}")

if __name__ == "__main__":
    upgrade()
