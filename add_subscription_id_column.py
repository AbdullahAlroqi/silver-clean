"""
Add subscription_id column to booking table
"""
import sqlite3
import os

# Check all possible database locations
db_paths = [
    'app.db',
    'instance/car_wash.db',
    'instance/silver_clean.db',
    'silver_clean.db'
]

base_dir = os.path.dirname(__file__)

for db_file in db_paths:
    db_path = os.path.join(base_dir, db_file)
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_file}")
        continue
        
    print(f"\nProcessing: {db_file}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if booking table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='booking'")
        if not cursor.fetchone():
            print(f"  - booking table not found in {db_file}")
            conn.close()
            continue
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(booking)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'subscription_id' not in columns:
            print(f"  - Adding subscription_id column...")
            cursor.execute("ALTER TABLE booking ADD COLUMN subscription_id INTEGER REFERENCES subscription(id)")
            conn.commit()
            print(f"  - Column added successfully!")
        else:
            print(f"  - Column subscription_id already exists.")
            
        conn.close()
        
    except Exception as e:
        print(f"  - Error: {e}")

print("\nMigration complete!")
