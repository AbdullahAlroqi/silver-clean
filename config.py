import os
import base64
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_vapid_private_key():
    value = os.environ.get('VAPID_PRIVATE_KEY') or 'private_key.pem'
    return value if os.path.isabs(value) else os.path.join(BASE_DIR, value)


def _resolve_vapid_public_key(private_key_path):
    configured = os.environ.get('VAPID_PUBLIC_KEY', '').strip()
    if configured:
        return configured
    try:
        from cryptography.hazmat.primitives import serialization
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(key_file.read(), password=None)
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )
        return base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('ascii')
    except (OSError, ValueError, TypeError):
        return ''


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
    
    # Session Configuration - 30 days duration (Reduced from 365 for security)
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_PERMANENT = True
    
    # Remember Me Cookie - 30 days duration
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = True  # Set to True for HTTPS
    SESSION_COOKIE_SECURE = True   # Set to True for HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True

    # VAPID Keys for Web Push Notifications
    VAPID_PRIVATE_KEY = _resolve_vapid_private_key()
    VAPID_PUBLIC_KEY = _resolve_vapid_public_key(VAPID_PRIVATE_KEY)
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:admin@silverclean.com')

    # Mail Settings - All from environment variables
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'info.silverclean1@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('ADMIN_EMAIL', 'silvcle.sa@gmail.com')]

    # Security Headers
    SESSION_COOKIE_SAMESITE = 'Lax'
