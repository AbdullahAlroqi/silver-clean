"""Migration script to add new columns and tables for city-based pricing and OSM integration"""
import sqlite3
import os

def migrate():
    # Find the database file
    db_path = None
    for p in ['instance/silver_clean.db', 'silver_clean.db', 'app.db', 'instance/app.db']:
        if os.path.exists(p):
            db_path = p
            break
    
    if not db_path:
        print("Database file not found!")
        return
    
    print(f"Using database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    changes = []
    
    # 1. Add osm_place_id to city table
    try:
        cursor.execute("ALTER TABLE city ADD COLUMN osm_place_id VARCHAR(50)")
        changes.append("Added osm_place_id to city")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  osm_place_id already exists in city")
        else:
            print(f"  Error: {e}")
    
    # 2. Add osm_name to neighborhood table
    try:
        cursor.execute("ALTER TABLE neighborhood ADD COLUMN osm_name VARCHAR(200)")
        changes.append("Added osm_name to neighborhood")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  osm_name already exists in neighborhood")
        else:
            print(f"  Error: {e}")
    
    # 3. Add is_active to product table
    try:
        cursor.execute("ALTER TABLE product ADD COLUMN is_active BOOLEAN DEFAULT 1")
        changes.append("Added is_active to product")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  is_active already exists in product")
        else:
            print(f"  Error: {e}")
    
    # 4. Create city_service_price table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_service_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                price FLOAT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (city_id) REFERENCES city(id),
                FOREIGN KEY (service_id) REFERENCES service(id),
                UNIQUE (city_id, service_id)
            )
        """)
        changes.append("Created city_service_price table")
    except sqlite3.OperationalError as e:
        print(f"  city_service_price error: {e}")
    
    # 5. Create city_product_price table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_product_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                price FLOAT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (city_id) REFERENCES city(id),
                FOREIGN KEY (product_id) REFERENCES product(id),
                UNIQUE (city_id, product_id)
            )
        """)
        changes.append("Created city_product_price table")
    except sqlite3.OperationalError as e:
        print(f"  city_product_price error: {e}")
    
    conn.commit()
    conn.close()
    
    if changes:
        print("\nMigration completed successfully:")
        for c in changes:
            print(f"  ✅ {c}")
    else:
        print("\nNo changes needed - all columns/tables already exist.")

if __name__ == '__main__':
    migrate()
