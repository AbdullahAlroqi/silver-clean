import sqlite3

def add_stock_column():
    db_path = 'instance/silver_clean.db'
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking if column 'stock_quantity' exists in 'product' table...")
        cursor.execute("SELECT stock_quantity FROM product LIMIT 1")
        print("Column 'stock_quantity' ALREADY EXISTS.")
    except sqlite3.OperationalError:
        print("Column missing. Adding 'stock_quantity' column...")
        try:
            cursor.execute("ALTER TABLE product ADD COLUMN stock_quantity INTEGER DEFAULT 0")
            conn.commit()
            print("Column 'stock_quantity' ADDED SUCCESSFULLY.")
        except Exception as e:
            print(f"FAILED to add column: {e}")
    finally:
        conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    add_stock_column()
