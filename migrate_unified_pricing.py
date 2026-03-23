import sqlite3
import os

DB_PATH = 'instance/silver_clean.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'silver_clean.db'

def migrate():
    print(f"🔍 Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='city_service_price'")
        if not cursor.fetchone():
            print("❌ city_service_price table not found. Skipping.")
            return

        # Check if column already exists
        cursor.execute("PRAGMA table_info(city_service_price)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'vehicle_size_id' in columns:
            print("⏭️ 'vehicle_size_id' already exists in city_service_price.")
            return

        print("🛠️ Starting migration for unified pricing...")

        # 1. Rename old table
        cursor.execute("ALTER TABLE city_service_price RENAME TO city_service_price_old")

        # 2. Create new table with vehicle_size_id and updated unique constraint
        cursor.execute('''
            CREATE TABLE city_service_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                vehicle_size_id INTEGER NOT NULL,
                price REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (city_id) REFERENCES city (id),
                FOREIGN KEY (service_id) REFERENCES service (id),
                FOREIGN KEY (vehicle_size_id) REFERENCES vehicle_size (id),
                UNIQUE (city_id, service_id, vehicle_size_id)
            )
        ''')

        # 3. Get all vehicle sizes
        cursor.execute("SELECT id FROM vehicle_size")
        sizes = [s[0] for s in cursor.fetchall()]
        if not sizes:
            print("⚠️ No vehicle sizes found. Using default size ID 1.")
            sizes = [1]

        # 4. Migrate data
        print("🔄 Migrating existing data...")
        cursor.execute("SELECT city_id, service_id, price, is_active FROM city_service_price_old")
        old_prices = cursor.fetchall()

        for city_id, service_id, price, is_active in old_prices:
            # For each old city-service override, create a record for each vehicle size
            # to maintain same price for all sizes in that city (old behavior)
            for size_id in sizes:
                cursor.execute('''
                    INSERT OR IGNORE INTO city_service_price (city_id, service_id, vehicle_size_id, price, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (city_id, service_id, size_id, price, is_active))

        # 5. Drop old table
        cursor.execute("DROP TABLE city_service_price_old")

        conn.commit()
        print("🎉 Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
