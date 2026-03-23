import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = 'instance/silver_clean.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'silver_clean.db'

def migrate():
    print(f"🔍 Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create service_size_price table
        print("🛠️ Creating service_size_price table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_size_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                vehicle_size_id INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (service_id) REFERENCES service (id),
                FOREIGN KEY (vehicle_size_id) REFERENCES vehicle_size (id)
            )
        ''')

        # 2. Create booking_item table
        print("🛠️ Creating booking_item table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS booking_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                service_price REAL DEFAULT 0.0,
                size_price_adjustment REAL DEFAULT 0.0,
                total_item_price REAL DEFAULT 0.0,
                FOREIGN KEY (booking_id) REFERENCES booking (id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicle (id),
                FOREIGN KEY (service_id) REFERENCES service (id)
            )
        ''')

        # 3. Add total_price and is_multi_vehicle to booking
        print("🛠️ Adding new columns to booking table...")
        try:
            cursor.execute('ALTER TABLE booking ADD COLUMN total_price REAL DEFAULT 0.0')
        except sqlite3.OperationalError:
            print("⏭️ 'total_price' already exists")
            
        try:
            cursor.execute('ALTER TABLE booking ADD COLUMN is_multi_vehicle BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            print("⏭️ 'is_multi_vehicle' already exists")

        # 4. Migrate existing booking data to booking_item
        print("🔄 Migrating existing bookings to items...")
        cursor.execute('SELECT id, vehicle_id, service_id, vehicle_size_price, custom_service_price FROM booking')
        bookings = cursor.fetchall()
        
        for booking_id, vehicle_id, service_id, size_adj, custom_price in bookings:
            # Skip bookings with missing vehicle or service (incomplete/bad records)
            if vehicle_id is None or service_id is None:
                print(f"⚠️ Skipping booking #{booking_id} due to missing vehicle or service")
                continue

            # Check if an item already exists for this booking to avoid duplicates
            cursor.execute('SELECT id FROM booking_item WHERE booking_id = ?', (booking_id,))
            if cursor.fetchone():
                continue
                
            # Get service base price if no custom price
            if custom_price is not None:
                base_price = float(custom_price)
            else:
                cursor.execute('SELECT price FROM service WHERE id = ?', (service_id,))
                res = cursor.fetchone()
                base_price = float(res[0]) if (res and res[0] is not None) else 0.0
            
            size_adj = float(size_adj) if size_adj is not None else 0.0
            total_item = base_price + size_adj
            
            cursor.execute('''
                INSERT INTO booking_item (booking_id, vehicle_id, service_id, service_price, size_price_adjustment, total_item_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (booking_id, vehicle_id, service_id, base_price, size_adj, total_item))
            
            # Update booking total_price
            cursor.execute('UPDATE booking SET total_price = ? WHERE id = ?', (total_item, booking_id))

        conn.commit()
        print("🎉 Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
