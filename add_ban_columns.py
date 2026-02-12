"""Add is_banned and ban_reason columns to user table"""
import sqlite3
import os

# Try both possible DB locations
db_paths = [
    os.path.join(os.path.dirname(__file__), 'silver_clean.db'),
    os.path.join(os.path.dirname(__file__), 'instance', 'silver_clean.db'),
]

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"Found DB: {db_path}")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        try:
            # Get existing columns
            cols = [x[1] for x in c.execute('PRAGMA table_info(user)').fetchall()]
            print(f"Existing columns: {cols}")
            
            if 'is_banned' not in cols:
                c.execute('ALTER TABLE user ADD COLUMN is_banned BOOLEAN DEFAULT 0')
                print("Added is_banned column")
            else:
                print("is_banned already exists")
                
            if 'ban_reason' not in cols:
                c.execute('ALTER TABLE user ADD COLUMN ban_reason VARCHAR(255)')
                print("Added ban_reason column")
            else:
                print("ban_reason already exists")
            
            conn.commit()
        except Exception as e:
            print(f"Error accessing user table: {e}")
        finally:
            conn.close()
        print("Done!")
    else:
        print(f"Skipping {db_path} (not found)")
