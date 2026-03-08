from functools import wraps
from flask import request, jsonify
from . import api_bp
from config import Config
from services import payment_service


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != Config.API_KEY:
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def api_response(data=None, message=None, status=200):
    """Standardized API response."""
    body = {'ok': status < 400}
    if data is not None:
        body['data'] = data
    if message:
        body['message'] = message
    return jsonify(body), status


def api_error(message, status=400):
    return jsonify({'ok': False, 'error': message}), status


@api_bp.route('/payments', methods=['GET'])
@require_api_key
def list_payments():
    year = request.args.get('year')
    payment_type = request.args.get('type')
    payments = payment_service.get_all_payments(year=year, payment_type=payment_type)
    return api_response([p.to_dict() for p in payments])


@api_bp.route('/payments', methods=['POST'])
@require_api_key
def create_payment():
    data = request.get_json(silent=True)
    if not data:
        return api_error('请求体必须为 JSON')
    if 'date' not in data or 'amount' not in data:
        return api_error('date 和 amount 为必填字段')
    try:
        float(data['amount'])
    except (ValueError, TypeError):
        return api_error('amount 必须为数字')

    payment, amount_changed = payment_service.create_payment(data)
    result = payment.to_dict()
    result['amount_changed'] = amount_changed
    return api_response(result, status=201)


@api_bp.route('/payments/<int:payment_id>', methods=['PUT'])
@require_api_key
def update_payment(payment_id):
    data = request.get_json(silent=True)
    if not data:
        return api_error('请求体必须为 JSON')
    payment, amount_changed = payment_service.update_payment(payment_id, data)
    if not payment:
        return api_error('记录不存在', 404)
    result = payment.to_dict()
    result['amount_changed'] = amount_changed
    return api_response(result)


@api_bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@require_api_key
def delete_payment(payment_id):
    if payment_service.delete_payment(payment_id):
        return api_response(message='已删除')
    return api_error('记录不存在', 404)


@api_bp.route('/stats/summary', methods=['GET'])
@require_api_key
def stats_summary():
    return api_response(payment_service.get_summary_stats())


@api_bp.route('/stats/trend', methods=['GET'])
@require_api_key
def stats_trend():
    return api_response(payment_service.get_monthly_trend())


@api_bp.route('/scheduler/config', methods=['GET'])
@require_api_key
def get_scheduler_config():
    config = payment_service.get_or_create_scheduler_config()
    return api_response(config.to_dict())


@api_bp.route('/scheduler/config', methods=['PUT'])
@require_api_key
def update_scheduler_config():
    data = request.get_json(silent=True)
    if not data:
        return api_error('请求体必须为 JSON')
    config = payment_service.update_scheduler_config(data)
    return api_response(config.to_dict())


@api_bp.route('/auth/token', methods=['POST'])
@require_api_key
def create_auth_token():
    """Generate a one-time login URL for a whitelisted TG user.

    Request: {"tg_id": "1308785881", "next": "/records"}
    Response: {"url": "/auth/tg?token=xxx"}
    """
    data = request.get_json(silent=True)
    if not data or 'tg_id' not in data:
        return api_error('tg_id 为必填字段')

    tg_id = str(data['tg_id'])
    if tg_id not in Config.TG_WHITELIST:
        return api_error('该用户不在白名单中', 403)

    from routes.auth import create_tg_token
    next_url = data.get('next', '/')
    token = create_tg_token(tg_id, next_url)
    url = f"/auth/tg?token={token}"
    return api_response({'url': url})
