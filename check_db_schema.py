from app import create_app, db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    if 'discount_code' in inspector.get_table_names():
        print("Table 'discount_code' exists.")
        columns = [c['name'] for c in inspector.get_columns('discount_code')]
        print(f"Columns: {columns}")
    else:
        print("Table 'discount_code' does NOT exist.")
