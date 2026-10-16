"""Create the saved_address table (customer's reusable booking locations)"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS saved_address (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES user(id),
                label VARCHAR(40) NOT NULL,
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL,
                city_id INTEGER REFERENCES city(id),
                neighborhood_id INTEGER REFERENCES neighborhood(id),
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("Created saved_address table.")
    except Exception as e:
        print(f"Error creating saved_address table: {e}")

    try:
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_saved_address_user_id ON saved_address (user_id)"
        ))
        print("Created index on saved_address.user_id.")
    except Exception as e:
        print(f"Error creating index: {e}")

    db.session.commit()
    print("Migration complete!")
