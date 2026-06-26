import sqlite3
import os

def fix_database():
    db_paths = ['silver_clean.db', 'instance/silver_clean.db']
    
    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue

        print(f"Updating database: {db_path}...")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            columns_to_add = [
                ('total_price', 'REAL DEFAULT 0.0'),
                ('is_multi_vehicle', 'BOOLEAN DEFAULT 0'),
                ('rating', 'INTEGER'),
                ('rating_comment', 'TEXT'),
                ('rating_date', 'DATETIME'),
                ('discount_code_id', 'INTEGER'),
                ('subscription_id', 'INTEGER'),
                ('used_free_wash', 'BOOLEAN DEFAULT 0'),
                ('vehicle_size_price', 'REAL DEFAULT 0.0'),
                ('custom_service_price', 'REAL'),
                ('payment_method', 'VARCHAR(20) DEFAULT "cash"'),
                ('started_at', 'DATETIME'),
                ('completed_at', 'DATETIME'),
                ('cancelled_at', 'DATETIME'),
                ('cancellation_reason', 'TEXT')
            ]
            
            cursor.execute("PRAGMA table_info(booking)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            added_count = 0
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    try:
                        print(f"  Adding column: {col_name}")
                        cursor.execute(f"ALTER TABLE booking ADD COLUMN {col_name} {col_type}")
                        added_count += 1
                    except Exception as e:
                        print(f"  Error adding {col_name}: {e}")
            
            conn.commit()
            conn.close()
            print(f"  Done. Added {added_count} columns to {db_path}.")
        except Exception as e:
            print(f"  Failed to update {db_path}: {e}")

if __name__ == "__main__":
    fix_database()
