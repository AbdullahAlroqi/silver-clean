from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    def get_locale():
        from flask import session, request
        # Check if language is in session
        if 'lang' in session:
            return session['lang']
        # Check if language is in request args (for testing)
        if request.args.get('lang'):
            return request.args.get('lang')
        # Default to Arabic
        return 'ar'

    # Initialize Babel
    from flask_babel import Babel
    babel = Babel(app, locale_selector=get_locale)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.customer import bp as customer_bp
    app.register_blueprint(customer_bp, url_prefix='/customer')

    from app.employee import bp as employee_bp
    app.register_blueprint(employee_bp, url_prefix='/employee')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_settings():
        from app.models import SiteSettings
        return dict(site_settings=SiteSettings.get_settings(), get_locale=get_locale)

    return app

from app import models
