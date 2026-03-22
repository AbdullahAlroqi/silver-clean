import os
import sys
from sqlalchemy import text, inspect

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app, db

def fix_all_schema():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        def add_column_if_missing(table_name, column_name, column_type):
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            if column_name not in columns:
                print(f"➕ Adding '{column_name}' to {table_name}...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                        conn.commit()
                    print(f"✅ Added {column_name}")
                except Exception as e:
                    print(f"❌ Error adding {column_name}: {e}")
            else:
                print(f"⏭️ {table_name}.{column_name} already exists")

        print("🔍 Checking Database Schema...")
        
        # Neighborhood Fixes
        add_column_if_missing('neighborhood', 'osm_name', 'VARCHAR(200)')
        add_column_if_missing('neighborhood', 'boundary_coords', 'TEXT')
        
        # City Fixes
        add_column_if_missing('city', 'osm_place_id', 'VARCHAR(50)')
        add_column_if_missing('city', 'is_active', 'BOOLEAN DEFAULT 1')
        
        # Product Fixes
        add_column_if_missing('product', 'stock_quantity', 'INTEGER DEFAULT 0')
        add_column_if_missing('product', 'is_active', 'BOOLEAN DEFAULT 1')
        add_column_if_missing('product', 'image_url', 'VARCHAR(255)')
        
        # Service Fixes
        add_column_if_missing('service', 'is_active', 'BOOLEAN DEFAULT 1')
        add_column_if_missing('service', 'includes_free_wash', 'BOOLEAN DEFAULT 1')
        
        # Site Settings Fixes
        add_column_if_missing('site_settings', 'referral_target_count', 'INTEGER DEFAULT 10')
        
        # User Fixes (Re-checking from referral script)
        add_column_if_missing('user', 'referral_code', 'VARCHAR(10)')
        add_column_if_missing('user', 'referred_by', 'INTEGER REFERENCES user(id)')
        add_column_if_missing('user', 'used_influencer_code_id', 'INTEGER REFERENCES discount_code(id)')
        
        # Discount Code Fixes
        add_column_if_missing('discount_code', 'is_influencer', 'BOOLEAN DEFAULT 0')
        add_column_if_missing('discount_code', 'influencer_name', 'VARCHAR(100)')

        print("🎉 Database schema check completed!")

if __name__ == "__main__":
    fix_all_schema()
