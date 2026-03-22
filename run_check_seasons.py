from app import create_app, db
from app.models import Season
app = create_app()
with app.app_context():
    seasons = Season.query.all()
    print([(s.id, s.name_ar, s.start_date, s.end_date, s.is_active) for s in seasons])
