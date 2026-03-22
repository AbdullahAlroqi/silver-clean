import os
import sys
from sqlalchemy import text, inspect

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app, db

def fix_neighborhood():
    app = create_app()
    with app.app_context():
        print("🔍 Checking neighborhood table columns...")
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('neighborhood')]
        
        with db.engine.connect() as conn:
            # 1. Add osm_name
            if 'osm_name' not in columns:
                print("➕ Adding 'osm_name' column to neighborhood...")
                try:
                    conn.execute(text("ALTER TABLE neighborhood ADD COLUMN osm_name VARCHAR(200)"))
                    conn.commit()
                    print("✅ Added 'osm_name'")
                except Exception as e:
                    print(f"❌ Error adding osm_name: {e}")
            else:
                print("⏭️ 'osm_name' already exists")
                
            # 2. Add boundary_coords
            if 'boundary_coords' not in columns:
                print("➕ Adding 'boundary_coords' column to neighborhood...")
                try:
                    conn.execute(text("ALTER TABLE neighborhood ADD COLUMN boundary_coords TEXT"))
                    conn.commit()
                    print("✅ Added 'boundary_coords'")
                except Exception as e:
                    print(f"❌ Error adding boundary_coords: {e}")
            else:
                print("⏭️ 'boundary_coords' already exists")

        print("🎉 Neighborhood fix completed!")

if __name__ == "__main__":
    fix_neighborhood()
