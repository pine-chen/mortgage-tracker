import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'mortgage.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # API Key for TG Bot authentication
    API_KEY = os.environ.get('MORTGAGE_API_KEY', 'change-me-in-production')

    # Web UI login (leave empty to disable)
    WEB_USERNAME = os.environ.get('MORTGAGE_WEB_USER', '')
    WEB_PASSWORD = os.environ.get('MORTGAGE_WEB_PASS', '')

    # Scheduler: set SCHEDULER_ENABLED=0 to disable (e.g. multi-worker Gunicorn)
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', '1') == '1'
    DEFAULT_PAYMENT_DAY = 18
    DEFAULT_MONTHLY_AMOUNT = 4230.0
    SCHEDULER_CHECK_HOUR = 8
    SCHEDULER_CHECK_MINUTE = 0

    # Logging
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')

    # Telegram whitelist: comma-separated user IDs that can get auto-login tokens
    TG_WHITELIST = [
        uid.strip() for uid in
        os.environ.get('TG_WHITELIST', '1308785881').split(',')
        if uid.strip()
    ]
    TG_TOKEN_EXPIRY = 300  # seconds (5 minutes)
