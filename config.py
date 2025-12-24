import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()


class Config:
    # ⚠️ SECURITY: All sensitive values MUST be set in .env file
    # Never commit .env to version control!
    
    # Flask Secret Key - REQUIRED for production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("⚠️ SECRET_KEY environment variable is not set! Create a .env file.")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///silver_clean.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Configuration - 1 year duration
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SESSION_PERMANENT = True
    
    # Remember Me Cookie - 1 year duration for PWA and browser
    REMEMBER_COOKIE_DURATION = timedelta(days=365)
    REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True

    # VAPID Keys for Web Push Notifications
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or os.path.join(os.path.dirname(__file__), 'private_key.pem')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:admin@silverclean.com')

    # Mail Settings - All from environment variables
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'info.silverclean1@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'zfqr qtzt duyw kiee')
    ADMINS = [os.environ.get('ADMIN_EMAIL', 'silvcle.sa@gmail.com')]
