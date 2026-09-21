# -*- coding: utf-8 -*-
"""认证：登录 / 登出"""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for

from app import db
from app.models import AdminUser
from app.utils.helpers import (ACCESS_VERIFY_SESSION_KEY, get_client_ip,
                                get_csrf_token, json_err, json_ok, log_action)

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if getattr(g, 'admin', None):
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html')

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    if not username or not password:
        return json_err('请输入账号和密码')

    user = AdminUser.query.filter_by(username=username).first()
    if user is None:
        return json_err('账号或密码错误')
    if user.status != 1:
        return json_err('该账号已被禁用，请联系超级管理员')

    now = datetime.now()
    max_fail = current_app.config['LOGIN_MAX_FAIL']
    lock_minutes = current_app.config['LOGIN_LOCK_MINUTES']

    if user.lock_until and user.lock_until > now:
        remain = int((user.lock_until - now).total_seconds() // 60) + 1
        return json_err('账号已被锁定，请 %d 分钟后再试' % remain)

    if not user.check_password(password):
        user.fail_count = (user.fail_count or 0) + 1
        if user.fail_count >= max_fail:
            user.fail_count = 0
            user.lock_until = now + timedelta(minutes=lock_minutes)
            db.session.commit()
            log_action('auth', 'login_fail', '账号 %s 密码连续错误，已锁定' % username)
            return json_err('密码错误次数过多，账号已锁定 %d 分钟' % lock_minutes)
        db.session.commit()
        return json_err('账号或密码错误，还可尝试 %d 次' % (max_fail - user.fail_count))

    # 登录成功
    user.fail_count = 0
    user.lock_until = None
    user.last_login_at = now
    user.last_login_ip = get_client_ip()
    db.session.commit()

    access_verified_at = session.get(ACCESS_VERIFY_SESSION_KEY)
    session.clear()
    if access_verified_at:
        session[ACCESS_VERIFY_SESSION_KEY] = access_verified_at
    session['admin_id'] = user.id
    session.permanent = True
    get_csrf_token()

    g.admin = user
    log_action('auth', 'login', '登录成功')

    return json_ok({'redirect': url_for('admin.dashboard')}, '登录成功')


@auth_bp.route('/logout')
def logout():
    if getattr(g, 'admin', None):
        log_action('auth', 'logout', '退出登录')
    access_verified_at = session.get(ACCESS_VERIFY_SESSION_KEY)
    session.clear()
    if access_verified_at:
        session[ACCESS_VERIFY_SESSION_KEY] = access_verified_at
    return redirect(url_for('auth.login'))
