import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-silver-clean'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///silver_clean.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # VAPID Keys for Web Push
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'BFwe-v4v5RXTcO6_qNhOjmsDmf011h2a1ktR6aBifvFlsn_l7HrRjh8YDfNjGwcCrtZB2Wiiu4tuHDlOecP2QjI'
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or os.path.join(os.path.dirname(__file__), 'private_key.pem')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL') or 'mailto:admin@silverclean.com'
