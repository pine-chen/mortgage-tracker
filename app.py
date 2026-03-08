import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Logging: console + rotating file
    fmt = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        Config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Session-based login for Web UI
    if Config.WEB_USERNAME and Config.WEB_PASSWORD:
        from flask import request, redirect, url_for, session

        @app.before_request
        def require_web_login():
            # API uses X-API-Key, skip session auth
            if request.path.startswith('/api/'):
                return
            # Static files, login page, and TG token login are always accessible
            if request.path.startswith('/static/') or request.path in ('/login', '/auth/tg'):
                return
            if not session.get('logged_in'):
                return redirect(url_for('auth.login', next=request.path))

    from routes import views_bp, api_bp
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Scheduler (can be disabled via env SCHEDULER_ENABLED=0)
    if Config.SCHEDULER_ENABLED:
        from services.scheduler_service import init_scheduler
        init_scheduler(app)
    else:
        logging.getLogger(__name__).info("Scheduler disabled by config.")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001, use_reloader=False)
