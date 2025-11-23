import sqlite3
import sys

def add_column():
    db_path = 'instance/silver_clean.db'
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Attempting to select push_subscription...")
        cursor.execute("SELECT push_subscription FROM user LIMIT 1")
        print("Column 'push_subscription' ALREADY EXISTS.")
    except sqlite3.OperationalError as e:
        print(f"Select failed: {e}")
        print("Adding 'push_subscription' column now...")
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN push_subscription TEXT")
            conn.commit()
            print("Column 'push_subscription' ADDED SUCCESSFULLY.")
        except Exception as e2:
            print(f"FAILED to add column: {e2}")
    except Exception as e3:
        print(f"Unexpected error: {e3}")
    finally:
        conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    add_column()
