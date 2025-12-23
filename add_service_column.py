from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(service)"))
            columns = [row[1] for row in result]
            
            if 'includes_free_wash' not in columns:
                print("Adding 'includes_free_wash' column to 'service' table...")
                conn.execute(text("ALTER TABLE service ADD COLUMN includes_free_wash BOOLEAN DEFAULT 1"))
                conn.commit()
                print("Column added successfully.")
            else:
                print("Column 'includes_free_wash' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")
