from flask import Blueprint

views_bp = Blueprint('views', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

from . import views, api  # noqa: E402, F401
