#!/usr/bin/env python3
"""
Migration script to create product_stock table for location-based inventory.
Run this script to update the database schema.
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'silver_clean.db')

# Check if the database file exists in instance folder
if not os.path.exists(db_path):
    # Try the old path
    db_path = os.path.join(os.path.dirname(__file__), 'silver_clean.db')

if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
    exit(1)

print(f"Connecting to database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if table already exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_stock'")
if cursor.fetchone():
    print("product_stock table already exists")
else:
    print("Creating product_stock table...")
    cursor.execute('''
        CREATE TABLE product_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES product(id),
            city_id INTEGER NOT NULL REFERENCES city(id),
            neighborhood_id INTEGER REFERENCES neighborhood(id),
            quantity INTEGER DEFAULT 0,
            UNIQUE(product_id, city_id, neighborhood_id)
        )
    ''')
    print("✓ product_stock table created")

conn.commit()
conn.close()

print("\n✅ Migration completed successfully!")
