from app import db, create_app
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS push_subscription"))
        conn.commit()
        print("Dropped push_subscription table")
