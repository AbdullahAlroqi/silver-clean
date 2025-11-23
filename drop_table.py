from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS subscription_package"))
        connection.commit()
        print("Table dropped")
