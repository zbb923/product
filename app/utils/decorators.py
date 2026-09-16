# -*- coding: utf-8 -*-
"""装饰器：登录校验、权限校验"""
from functools import wraps

from flask import g, redirect, request, url_for

from app.utils.helpers import is_ajax, json_err


def login_required(view):
    """后台登录校验：未登录跳转登录页，AJAX 返回 401"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if getattr(g, 'admin', None) is None:
            if is_ajax():
                return json_err('登录状态已失效，请重新登录', code=401), 401
            return redirect(url_for('auth.login', next=request.full_path))
        return view(*args, **kwargs)
    return wrapper


def permission_required(code):
    """权限点校验，需配合 login_required 使用"""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            admin = getattr(g, 'admin', None)
            if admin is None:
                if is_ajax():
                    return json_err('登录状态已失效，请重新登录', code=401), 401
                return redirect(url_for('auth.login', next=request.full_path))
            if not admin.has_permission(code):
                if is_ajax():
                    return json_err('您没有该操作权限', code=403), 403
                return '您没有该操作权限', 403
            return view(*args, **kwargs)
        return wrapper
    return decorator
