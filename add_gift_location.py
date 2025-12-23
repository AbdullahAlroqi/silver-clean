#!/usr/bin/env python3
"""
Migration script to add city_id and neighborhood_id columns to gift_order table
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

# Check if columns already exist
cursor.execute("PRAGMA table_info(gift_order)")
columns = [column[1] for column in cursor.fetchall()]

if 'city_id' not in columns:
    print("Adding city_id column to gift_order table...")
    cursor.execute("ALTER TABLE gift_order ADD COLUMN city_id INTEGER REFERENCES city(id)")
    print("✓ city_id column added")
else:
    print("city_id column already exists")

if 'neighborhood_id' not in columns:
    print("Adding neighborhood_id column to gift_order table...")
    cursor.execute("ALTER TABLE gift_order ADD COLUMN neighborhood_id INTEGER REFERENCES neighborhood(id)")
    print("✓ neighborhood_id column added")
else:
    print("neighborhood_id column already exists")

conn.commit()
conn.close()

print("\n✅ Migration completed successfully!")
