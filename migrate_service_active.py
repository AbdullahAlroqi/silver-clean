from app import create_app, db
from app.models import Service
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Check if column exists
        db.session.execute(text("SELECT is_active FROM service LIMIT 1"))
        print("Column 'is_active' already exists in 'service' table.")
    except Exception:
        db.session.rollback()
        print("Adding 'is_active' column to 'service' table...")
        # For MySQL/PostgreSQL (likely on Hostinger)
        db.session.execute(text("ALTER TABLE service ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        db.session.commit()
        print("Successfully added 'is_active' column.")
