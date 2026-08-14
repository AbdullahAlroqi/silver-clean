from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
from flask_mail import Mail
mail = Mail()
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app(config_class=Config):
    # Import once so SQLAlchemy session audit listeners are registered.
    from app import audit  # noqa: F401
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    
    from app.limiter import limiter
    limiter.init_app(app)
    
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

    @app.before_request
    def check_banned():
        from flask_login import current_user, logout_user
        from flask import redirect, url_for, flash, request, render_template
        from app.models import SiteSettings

        if request.endpoint != 'static':
            settings = SiteSettings.get_settings()
            if getattr(settings, 'maintenance_mode', False):
                auth_endpoint = request.endpoint in ['auth.login', 'auth.logout']
                admin_settings_endpoint = request.endpoint == 'admin.settings'
                authenticated_entry_endpoint = (
                    request.endpoint == 'main.index'
                    and current_user.is_authenticated
                    and current_user.role in ['admin', 'supervisor', 'site_supervisor']
                )
                allowed_endpoint = auth_endpoint or admin_settings_endpoint or authenticated_entry_endpoint

                if not allowed_endpoint:
                    return render_template('maintenance.html', settings=settings), 503

        if current_user.is_authenticated and getattr(current_user, 'is_banned', False):
            logout_user()
            flash('تم حظر حسابك بشكل نهائي. للتواصل مع الإدارة يرجى الاتصال بالدعم.', 'error')
            if request.endpoint != 'auth.login':
                return redirect(url_for('auth.login'))

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app

from app import models
