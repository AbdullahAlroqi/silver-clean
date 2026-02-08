"""
Migration script to add timer and cancellation fields to the Booking table.
Run this script to update your database schema.
"""
from app import create_app, db
from sqlalchemy import text

def add_booking_timer_fields():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        
        # Check and add each column if it doesn't exist
        columns_to_add = [
            ('started_at', 'DATETIME'),
            ('completed_at', 'DATETIME'),
            ('cancelled_at', 'DATETIME'),
            ('cancellation_reason', 'TEXT'),
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                # Check if column exists
                result = conn.execute(text(f"PRAGMA table_info(booking)"))
                columns = [row[1] for row in result.fetchall()]
                
                if column_name not in columns:
                    conn.execute(text(f"ALTER TABLE booking ADD COLUMN {column_name} {column_type}"))
                    print(f"✓ Added column: {column_name}")
                else:
                    print(f"- Column already exists: {column_name}")
            except Exception as e:
                print(f"✗ Error adding {column_name}: {e}")
        
        conn.commit()
        conn.close()
        print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    add_booking_timer_fields()
