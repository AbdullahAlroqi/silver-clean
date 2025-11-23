from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        with db.engine.connect() as connection:
            connection.execute(text('DROP TABLE IF EXISTS _alembic_tmp_subscription'))
            connection.commit()
        print("Dropped _alembic_tmp_subscription table.")
    except Exception as e:
        print(f"Error: {e}")
