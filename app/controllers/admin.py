# -*- coding: utf-8 -*-
"""后台通用：控制台、个人中心、操作日志"""
from flask import Blueprint, g, render_template, request, session, url_for

from app import db
from app.models import AdminLog, AdminRole, AdminUser, Product, ProductCategory
from app.utils.decorators import login_required, permission_required
from app.utils.helpers import json_err, json_ok, log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== 控制台 ====================

@admin_bp.route('/')
@permission_required('dashboard')
def dashboard():
    stats = {
        'product_total': Product.query.count(),
        'product_on': Product.query.filter_by(status=1).count(),
        'product_off': Product.query.filter_by(status=0).count(),
        'category_total': ProductCategory.query.count(),
        'user_total': AdminUser.query.count(),
        'role_total': AdminRole.query.count(),
        'views_total': db.session.query(db.func.coalesce(db.func.sum(Product.views), 0)).scalar(),
    }
    recent_products = Product.query.order_by(Product.id.desc()).limit(6).all()
    recent_logs = AdminLog.query.order_by(AdminLog.id.desc()).limit(8).all()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_products=recent_products, recent_logs=recent_logs)


# ==================== 个人中心 ====================

@admin_bp.route('/profile')
@login_required
def profile():
    return render_template('admin/profile.html')


@admin_bp.route('/profile', methods=['POST'])
@login_required
def profile_update():
    admin = g.admin
    real_name = (request.form.get('real_name') or '').strip()
    avatar = (request.form.get('avatar') or '').strip()
    if len(real_name) > 50:
        return json_err('姓名长度不能超过 50 个字符')
    admin.real_name = real_name
    admin.avatar = avatar
    db.session.commit()
    log_action('profile', 'edit', '修改个人资料')
    return json_ok(msg='保存成功')


@admin_bp.route('/profile/password', methods=['POST'])
@login_required
def profile_password():
    admin = g.admin
    old_pwd = request.form.get('old_password') or ''
    new_pwd = request.form.get('new_password') or ''
    confirm = request.form.get('confirm_password') or ''

    if not admin.check_password(old_pwd):
        return json_err('原密码不正确')
    if len(new_pwd) < 6:
        return json_err('新密码长度不能少于 6 位')
    if new_pwd != confirm:
        return json_err('两次输入的新密码不一致')

    admin.set_password(new_pwd)
    admin.fail_count = 0
    admin.lock_until = None
    db.session.commit()
    log_action('profile', 'password', '修改登录密码')

    session.clear()
    return json_ok({'redirect': url_for('auth.login')}, '密码修改成功，请重新登录')


# ==================== 操作日志 ====================

@admin_bp.route('/log')
@permission_required('log:list')
def log_list():
    return render_template('admin/log/list.html')


@admin_bp.route('/log/data')
@permission_required('log:list')
def log_data():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('limit', 15, type=int)
    keyword = (request.args.get('keyword') or '').strip()
    module = (request.args.get('module') or '').strip()

    query = AdminLog.query
    if keyword:
        query = query.filter(db.or_(
            AdminLog.username.like('%%%s%%' % keyword),
            AdminLog.content.like('%%%s%%' % keyword),
        ))
    if module:
        query = query.filter(AdminLog.module == module)

    pagination = query.order_by(AdminLog.id.desc()).paginate(page=page, per_page=size, error_out=False)
    rows = [{
        'id': item.id,
        'username': item.username,
        'module': item.module,
        'action': item.action,
        'content': item.content,
        'ip': item.ip,
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
    } for item in pagination.items]

    return json_ok({'items': rows, 'total': pagination.total})
