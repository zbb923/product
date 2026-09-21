# -*- coding: utf-8 -*-
"""
通用工具：
- 统一 JSON 响应
- 操作日志
- CSRF 防护
- 访问验证码校验
- 模板全局变量（当前登录人、权限集合、侧边菜单）
"""
import secrets
import time
from datetime import datetime
from decimal import Decimal

from flask import current_app, g, jsonify, redirect, request, session, url_for

from app import db

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')
CSRF_SESSION_KEY = '_csrf_token'
ACCESS_VERIFY_SESSION_KEY = 'access_verified_at'


# ==================== 响应 ====================

def json_ok(data=None, msg='操作成功'):
    return jsonify({'code': 0, 'msg': msg, 'data': data})


def json_err(msg='操作失败', code=1, data=None):
    return jsonify({'code': code, 'msg': msg, 'data': data})


# ==================== 请求辅助 ====================

def is_ajax():
    """判断是否为 AJAX / JSON 请求"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.headers.get('X-CSRF-Token'):
        return True
    if 'application/json' in (request.headers.get('Accept') or ''):
        return True
    return False


def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''


# ==================== CSRF ====================

def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(16)
        session[CSRF_SESSION_KEY] = token
    return token


def _check_csrf():
    token = session.get(CSRF_SESSION_KEY)
    sent = request.headers.get('X-CSRF-Token') or request.form.get('_csrf') or ''
    return bool(token) and secrets.compare_digest(str(token), str(sent))


# ==================== 访问验证码 ====================

def is_access_verified():
    """检查 session 中的访问验证是否在有效期内"""
    ts = session.get(ACCESS_VERIFY_SESSION_KEY)
    if not ts:
        return False
    minutes = current_app.config.get('ACCESS_VERIFY_MINUTES', 15)
    return (time.time() - ts) < minutes * 60


def set_access_verified():
    """写入访问验证时间戳"""
    session[ACCESS_VERIFY_SESSION_KEY] = time.time()


def _is_exempt_from_access_verify():
    """静态资源与验证页本身免校验"""
    if request.path.startswith('/static/'):
        return True
    if request.endpoint == 'front.access_verify':
        return True
    return False


# ==================== 操作日志 ====================

def log_action(module, action, content=''):
    """写入后台操作日志"""
    from app.models.system import AdminLog
    admin = getattr(g, 'admin', None)
    try:
        db.session.add(AdminLog(
            user_id=admin.id if admin else None,
            username=admin.username if admin else '匿名',
            module=module,
            action=action,
            content=str(content)[:2000],
            ip=get_client_ip(),
        ))
        db.session.commit()
    except Exception:  # 日志失败不影响主流程
        db.session.rollback()


# ==================== 模板辅助 ====================

def money(value):
    """金额格式化：整数不带小数"""
    if value is None:
        return '0'
    value = Decimal(str(value))
    if value == value.to_integral_value():
        return str(int(value))
    return '%.2f' % value


def dt(value, fmt='%Y-%m-%d %H:%M:%S'):
    if not value:
        return ''
    if isinstance(value, str):
        return value
    return value.strftime(fmt)


def _current_admin():
    """从 session 载入当前登录管理员"""
    from app.models.system import AdminUser
    admin_id = session.get('admin_id')
    if not admin_id:
        return None
    admin = db.session.get(AdminUser, admin_id)
    if admin is None or admin.status != 1:
        session.pop('admin_id', None)
        return None
    return admin


def _build_menus(admin):
    """按权限生成侧边菜单（仅一级菜单）"""
    from app.models.system import AdminPermission
    query = AdminPermission.query.filter_by(type=1, status=1)
    if not admin.is_super:
        codes = list(admin.permission_code_set())
        if not codes:
            return []
        query = query.filter(AdminPermission.code.in_(codes))
    return query.order_by(AdminPermission.sort.asc(), AdminPermission.id.asc()).all()


def register_app(app):
    """注册请求钩子与模板全局"""

    @app.before_request
    def _before_request():
        g.admin = _current_admin()
        # 非安全方法统一做 CSRF 校验
        if request.method not in SAFE_METHODS and not _check_csrf():
            if is_ajax():
                return json_err('请求已失效，请刷新页面后重试', code=403), 403
            return '请求已失效，请返回上一页刷新后重试', 403
        # 访问验证码校验（静态资源与验证页本身跳过）
        if not _is_exempt_from_access_verify() and not is_access_verified():
            if is_ajax():
                return json_err('访问验证已过期，请重新验证', code=403), 403
            return redirect(url_for('front.access_verify', next=request.full_path))
        # 后台页面禁用缓存，避免退出后回退仍可见
        if request.path.startswith('/admin'):
            g.no_cache = True

    @app.after_request
    def _after_request(response):
        if getattr(g, 'no_cache', False):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        return response

    @app.context_processor
    def _inject_globals():
        admin = getattr(g, 'admin', None)
        return {
            'current_admin': admin,
            'csrf_token': get_csrf_token(),
            'menus': _build_menus(admin) if admin else [],
            'site_name': app.config.get('SITE_NAME', '产品报价中心'),
            'site_slogan': app.config.get('SITE_SLOGAN', ''),
            'current_path': request.path,
        }

    def has_perm(code):
        admin = getattr(g, 'admin', None)
        if admin is None:
            return False
        return admin.has_permission(code)

    app.jinja_env.globals['has_perm'] = has_perm

    @app.errorhandler(404)
    def _404(e):
        if is_ajax():
            return json_err('接口不存在', code=404)
        return '页面不存在', 404

    @app.errorhandler(413)
    def _413(e):
        return json_err('上传文件过大，单文件最大 10MB', code=413)

    @app.errorhandler(500)
    def _500(e):
        db.session.rollback()
        if is_ajax():
            return json_err('服务器内部错误', code=500)
        return '服务器内部错误', 500

    return app
