import sqlite3
import os

paths = [
    os.path.join(os.path.dirname(__file__), 'instance', 'silver_clean.db'),
    os.path.join(os.path.dirname(__file__), 'silver_clean.db'),
    os.path.join(os.path.dirname(__file__), 'app.db')
]

for path in paths:
    if os.path.exists(path):
        print(f"Trying {path}...")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE season ADD COLUMN allow_free_washes BOOLEAN DEFAULT 0;")
            conn.commit()
            conn.close()
            print(f"Successfully added column to {path}")
            break
        except Exception as e:
            print(f"Error on {path}: {e}")
