import secrets
import time
from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from config import Config

auth_bp = Blueprint('auth', __name__)

# In-memory token store: {token: {'tg_id': str, 'expires': float, 'next': str}}
_pending_tokens = {}


def _cleanup_tokens():
    """Remove expired tokens."""
    now = time.time()
    expired = [t for t, v in _pending_tokens.items() if v['expires'] < now]
    for t in expired:
        _pending_tokens.pop(t, None)


def create_tg_token(tg_id, next_url='/'):
    """Generate a one-time login token for a whitelisted TG user."""
    _cleanup_tokens()
    token = secrets.token_urlsafe(32)
    _pending_tokens[token] = {
        'tg_id': str(tg_id),
        'expires': time.time() + Config.TG_TOKEN_EXPIRY,
        'next': next_url,
    }
    return token


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == Config.WEB_USERNAME and password == Config.WEB_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            next_url = request.args.get('next', '/')
            return redirect(next_url)
        flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@auth_bp.route('/auth/tg')
def tg_login():
    """One-click login via TG bot token."""
    token = request.args.get('token', '')
    _cleanup_tokens()
    token_data = _pending_tokens.pop(token, None)

    if not token_data:
        flash('链接已失效或已使用，请重新获取', 'danger')
        return redirect(url_for('auth.login'))

    if token_data['expires'] < time.time():
        flash('链接已过期，请重新获取', 'danger')
        return redirect(url_for('auth.login'))

    session['logged_in'] = True
    session['tg_id'] = token_data['tg_id']
    session.permanent = True
    return redirect(token_data.get('next', '/'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
