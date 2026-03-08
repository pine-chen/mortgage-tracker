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

    # Web UI basic auth (skip for API routes)
    if Config.WEB_USERNAME and Config.WEB_PASSWORD:
        from functools import wraps
        from flask import request, Response

        def check_web_auth(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth or auth.username != Config.WEB_USERNAME or auth.password != Config.WEB_PASSWORD:
                    return Response(
                        '需要登录', 401,
                        {'WWW-Authenticate': 'Basic realm="Mortgage Tracker"'}
                    )
                return f(*args, **kwargs)
            return decorated

        @app.before_request
        def require_web_login():
            if request.path.startswith('/api/'):
                return  # API uses X-API-Key, skip basic auth
            if request.path.startswith('/static/'):
                return
            auth = request.authorization
            if not auth or auth.username != Config.WEB_USERNAME or auth.password != Config.WEB_PASSWORD:
                return Response(
                    '需要登录', 401,
                    {'WWW-Authenticate': 'Basic realm="Mortgage Tracker"'}
                )

    from routes import views_bp, api_bp
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
