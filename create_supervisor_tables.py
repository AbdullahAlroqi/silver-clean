from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Create supervisor_cities table
    try:
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS supervisor_cities (
                user_id INTEGER NOT NULL,
                city_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, city_id),
                FOREIGN KEY(user_id) REFERENCES user (id),
                FOREIGN KEY(city_id) REFERENCES city (id)
            )
        '''))
        print("✅ Created supervisor_cities table")
    except Exception as e:
        print(f"❌ Error creating supervisor_cities table: {e}")

    # Create supervisor_neighborhoods table
    try:
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS supervisor_neighborhoods (
                user_id INTEGER NOT NULL,
                neighborhood_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, neighborhood_id),
                FOREIGN KEY(user_id) REFERENCES user (id),
                FOREIGN KEY(neighborhood_id) REFERENCES neighborhood (id)
            )
        '''))
        print("✅ Created supervisor_neighborhoods table")
    except Exception as e:
        print(f"❌ Error creating supervisor_neighborhoods table: {e}")

    db.session.commit()
