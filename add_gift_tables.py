"""Create gift_order and gift_order_product tables"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Create gift_order table
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS gift_order (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER REFERENCES user(id),
                recipient_name VARCHAR(100),
                recipient_phone VARCHAR(20),
                gift_type VARCHAR(20),
                service_id INTEGER REFERENCES service(id),
                package_id INTEGER REFERENCES subscription_package(id),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("Created gift_order table.")
    except Exception as e:
        print(f"Error creating gift_order table: {e}")

    # Create gift_order_product table
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS gift_order_product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_order_id INTEGER REFERENCES gift_order(id),
                product_id INTEGER REFERENCES product(id),
                quantity INTEGER DEFAULT 1
            )
        """))
        print("Created gift_order_product table.")
    except Exception as e:
        print(f"Error creating gift_order_product table: {e}")

    db.session.commit()
    print("Migration complete!")
