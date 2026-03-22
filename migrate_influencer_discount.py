import sqlite3
from app import create_app, db

def upgrade():
    app = create_app()
    with app.app_context():
        print("Starting influencer discount migration within Flask app context...")
        
        # We can use raw engine execution for ALTER TABLE in SQLite
        with db.engine.connect() as conn:
            # 1. Add used_influencer_code_id to User table
            print("Adding used_influencer_code_id to user table...")
            try:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN used_influencer_code_id INTEGER REFERENCES discount_code(id)"))
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(" -> used_influencer_code_id already exists")
                else:
                    print(f"Error adding column to user: {e}")
            
            # 2. Add influencer columns to DiscountCode table
            print("Adding influencer columns to discount_code table...")
            try:
                conn.execute(db.text("ALTER TABLE discount_code ADD COLUMN is_influencer BOOLEAN DEFAULT 0"))
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(" -> is_influencer already exists")
                else:
                    print(f"Error adding is_influencer: {e}")
                    
            try:
                conn.execute(db.text("ALTER TABLE discount_code ADD COLUMN influencer_name VARCHAR(100)"))
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(" -> influencer_name already exists")
                else:
                    print(f"Error adding influencer_name: {e}")
            
            # 3. Drop the old influencer_code table
            print("Dropping old influencer_code table if it exists...")
            try:
                conn.execute(db.text("DROP TABLE IF EXISTS influencer_code"))
            except Exception as e:
                print(f"Error dropping table: {e}")
                
            conn.commit()
            print("Migration completed!")

if __name__ == '__main__':
    upgrade()
    
