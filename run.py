from app import create_app, db
from app.models import User, Service, Booking, City, Neighborhood

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Service': Service, 'Booking': Booking, 'City': City, 'Neighborhood': Neighborhood}

if __name__ == '__main__':
    app.run(debug=True)
