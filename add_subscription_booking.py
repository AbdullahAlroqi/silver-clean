"""Add subscription_id to Booking model"""
from app import db, create_app
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Check if column exists
    try:
        db.session.execute(text("SELECT subscription_id FROM booking LIMIT 1"))
        print("Column 'subscription_id' already exists in booking table.")
    except Exception:
        # Add the column
        db.session.execute(text("ALTER TABLE booking ADD COLUMN subscription_id INTEGER REFERENCES subscription(id)"))
        db.session.commit()
        print("Added 'subscription_id' column to booking table.")
