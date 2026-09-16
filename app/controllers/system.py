# -*- coding: utf-8 -*-
"""系统管理：管理员、角色（权限组）、权限"""
from flask import Blueprint, current_app, g, jsonify, render_template, request

from app import db
from app.models import AdminPermission, AdminRole, AdminUser
from app.utils.decorators import permission_required
from app.utils.helpers import json_err, json_ok, log_action

system_bp = Blueprint('system', __name__, url_prefix='/admin')


def _table_json(items, total):
    return jsonify({'code': 0, 'msg': '', 'count': total, 'data': items})


def _parse_ids(raw):
    """解析逗号分隔的 ID 字符串为整数列表"""
    if not raw:
        return []
    result = []
    for part in str(raw).split(','):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return sorted(set(result))


def _super_role_id():
    return current_app.config.get('SUPER_ROLE_ID', 1)


# ==================== 管理员管理 ====================

@system_bp.route('/user')
@permission_required('user:list')
def user_list():
    roles = AdminRole.query.order_by(AdminRole.id.asc()).all()
    return render_template('admin/user/list.html', roles=roles)


@system_bp.route('/user/data')
@permission_required('user:list')
def user_data():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('limit', 15, type=int)
    keyword = (request.args.get('keyword') or '').strip()

    query = AdminUser.query
    if keyword:
        query = query.filter(db.or_(
            AdminUser.username.like('%%%s%%' % keyword),
            AdminUser.real_name.like('%%%s%%' % keyword),
        ))

    pagination = query.order_by(AdminUser.id.asc()).paginate(page=page, per_page=size, error_out=False)
    super_id = _super_role_id()

    rows = []
    for item in pagination.items:
        rows.append({
            'id': item.id,
            'username': item.username,
            'real_name': item.real_name or '',
            'role_ids': [r.id for r in item.roles],
            'role_names': item.role_names(),
            'status': item.status,
            'is_super': any(r.id == super_id for r in item.roles),
            'last_login_at': item.last_login_at.strftime('%Y-%m-%d %H:%M') if item.last_login_at else '从未登录',
            'last_login_ip': item.last_login_ip or '',
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '',
        })
    return _table_json(rows, pagination.total)


@system_bp.route('/user/add', methods=['POST'])
@permission_required('user:add')
def user_add():
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    real_name = (request.form.get('real_name') or '').strip()

    if not username:
        return json_err('请填写登录账号')
    if len(username) > 50:
        return json_err('登录账号不能超过 50 个字符')
    if not username.replace('_', '').isalnum():
        return json_err('登录账号仅支持字母、数字和下划线')
    if AdminUser.query.filter_by(username=username).first():
        return json_err('该登录账号已存在')
    if len(password) < 6:
        return json_err('登录密码长度不能少于 6 位')

    role_ids = _parse_ids(request.form.get('role_ids'))
    if not role_ids:
        return json_err('请至少选择一个角色')
    roles = AdminRole.query.filter(AdminRole.id.in_(role_ids)).all()
    if len(roles) != len(role_ids):
        return json_err('所选角色不存在')

    user = AdminUser(
        username=username,
        real_name=real_name,
        status=1 if request.form.get('status', '1') == '1' else 0,
    )
    user.set_password(password)
    user.roles = roles
    db.session.add(user)
    db.session.commit()
    log_action('user', 'add', '新增管理员：%s' % username)
    return json_ok(msg='新增成功')


@system_bp.route('/user/edit/<int:uid>', methods=['POST'])
@permission_required('user:edit')
def user_edit(uid):
    user = db.session.get(AdminUser, uid)
    if user is None:
        return json_err('管理员不存在')

    real_name = (request.form.get('real_name') or '').strip()
    role_ids = _parse_ids(request.form.get('role_ids'))
    if not role_ids:
        return json_err('请至少选择一个角色')
    roles = AdminRole.query.filter(AdminRole.id.in_(role_ids)).all()
    if len(roles) != len(role_ids):
        return json_err('所选角色不存在')

    is_super_user = any(r.id == _super_role_id() for r in user.roles)
    if is_super_user and not any(r.id == _super_role_id() for r in roles):
        return json_err('不能取消超级管理员的超级管理员角色')

    password = request.form.get('password') or ''
    if password and len(password) < 6:
        return json_err('登录密码长度不能少于 6 位')

    user.real_name = real_name
    user.roles = roles
    if user.id != 1:  # 账号 1 为初始超管，不允许被禁用
        user.status = 1 if request.form.get('status', '1') == '1' else 0
    if password:
        user.set_password(password)
        user.fail_count = 0
        user.lock_until = None
    db.session.commit()
    log_action('user', 'edit', '编辑管理员：%s' % user.username)
    return json_ok(msg='保存成功')


@system_bp.route('/user/delete/<int:uid>', methods=['POST'])
@permission_required('user:delete')
def user_delete(uid):
    user = db.session.get(AdminUser, uid)
    if user is None:
        return json_err('管理员不存在')
    if user.id == g.admin.id:
        return json_err('不能删除当前登录的账号')
    if user.id == 1:
        return json_err('初始超级管理员账号不允许删除')

    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action('user', 'delete', '删除管理员：%s' % username)
    return json_ok(msg='删除成功')


@system_bp.route('/user/toggle/<int:uid>', methods=['POST'])
@permission_required('user:edit')
def user_toggle(uid):
    user = db.session.get(AdminUser, uid)
    if user is None:
        return json_err('管理员不存在')
    if user.id == g.admin.id:
        return json_err('不能禁用当前登录的账号')
    if user.id == 1:
        return json_err('初始超级管理员账号不允许禁用')
    user.status = 0 if user.status == 1 else 1
    db.session.commit()
    log_action('user', 'edit', '%s管理员：%s' % ('启用' if user.status == 1 else '禁用', user.username))
    return json_ok({'status': user.status}, '操作成功')


@system_bp.route('/user/resetpwd/<int:uid>', methods=['POST'])
@permission_required('user:edit')
def user_resetpwd(uid):
    user = db.session.get(AdminUser, uid)
    if user is None:
        return json_err('管理员不存在')
    password = (request.form.get('password') or '').strip() or '123456'
    if len(password) < 6:
        return json_err('新密码长度不能少于 6 位')
    user.set_password(password)
    user.fail_count = 0
    user.lock_until = None
    db.session.commit()
    log_action('user', 'edit', '重置管理员密码：%s' % user.username)
    return json_ok(msg='密码已重置')


# ==================== 角色管理 ====================

@system_bp.route('/role')
@permission_required('role:list')
def role_list():
    return render_template('admin/role/list.html')


@system_bp.route('/role/data')
@permission_required('role:list')
def role_data():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('limit', 15, type=int)
    keyword = (request.args.get('keyword') or '').strip()

    query = AdminRole.query
    if keyword:
        query = query.filter(AdminRole.name.like('%%%s%%' % keyword))

    pagination = query.order_by(AdminRole.id.asc()).paginate(page=page, per_page=size, error_out=False)
    super_id = _super_role_id()

    rows = [{
        'id': item.id,
        'name': item.name,
        'description': item.description or '',
        'status': item.status,
        'is_super': item.id == super_id,
        'perm_count': len(item.permissions),
        'user_count': len(item.users),
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '',
    } for item in pagination.items]
    return _table_json(rows, pagination.total)


@system_bp.route('/role/add', methods=['POST'])
@permission_required('role:add')
def role_add():
    name = (request.form.get('name') or '').strip()
    if not name:
        return json_err('请填写角色名称')
    if len(name) > 50:
        return json_err('角色名称不能超过 50 个字符')
    if AdminRole.query.filter_by(name=name).first():
        return json_err('该角色名称已存在')

    role = AdminRole(
        name=name,
        description=(request.form.get('description') or '').strip()[:255],
        status=1 if request.form.get('status', '1') == '1' else 0,
    )
    db.session.add(role)
    db.session.commit()
    log_action('role', 'add', '新增角色：%s' % name)
    return json_ok(msg='新增成功')


@system_bp.route('/role/edit/<int:rid>', methods=['POST'])
@permission_required('role:edit')
def role_edit(rid):
    role = db.session.get(AdminRole, rid)
    if role is None:
        return json_err('角色不存在')

    name = (request.form.get('name') or '').strip()
    if not name:
        return json_err('请填写角色名称')
    if len(name) > 50:
        return json_err('角色名称不能超过 50 个字符')
    if AdminRole.query.filter(AdminRole.name == name, AdminRole.id != rid).first():
        return json_err('该角色名称已存在')

    role.name = name
    role.description = (request.form.get('description') or '').strip()[:255]
    if not role.is_super:  # 超级管理员角色不允许被禁用
        role.status = 1 if request.form.get('status', '1') == '1' else 0
    db.session.commit()
    log_action('role', 'edit', '编辑角色：%s' % name)
    return json_ok(msg='保存成功')


@system_bp.route('/role/delete/<int:rid>', methods=['POST'])
@permission_required('role:delete')
def role_delete(rid):
    role = db.session.get(AdminRole, rid)
    if role is None:
        return json_err('角色不存在')
    if role.is_super:
        return json_err('超级管理员角色不允许删除')
    if len(role.users) > 0:
        return json_err('该角色下还有管理员，请先解除关联')

    name = role.name
    db.session.delete(role)
    db.session.commit()
    log_action('role', 'delete', '删除角色：%s' % name)
    return json_ok(msg='删除成功')


@system_bp.route('/role/permission/<int:rid>', methods=['GET', 'POST'])
@permission_required('role:edit')
def role_permission(rid):
    role = db.session.get(AdminRole, rid)
    if role is None:
        if request.method == 'GET':
            return '角色不存在', 404
        return json_err('角色不存在')

    if request.method == 'GET':
        checked_ids = [p.id for p in role.permissions]
        return render_template('admin/role/permission.html', role=role,
                               perm_tree=_build_perm_tree(checked_ids))

    if role.is_super:
        return json_err('超级管理员默认拥有全部权限，无需单独配置')

    perm_ids = _parse_ids(request.form.get('perm_ids'))
    perms = AdminPermission.query.all()
    perm_map = {p.id: p for p in perms}

    # 自动补齐所选权限的父级，保证菜单可见
    final_ids = set()
    for pid in perm_ids:
        node = perm_map.get(pid)
        while node is not None and node.id not in final_ids:
            final_ids.add(node.id)
            node = perm_map.get(node.parent_id)

    role.permissions = [perm_map[pid] for pid in final_ids if pid in perm_map]
    db.session.commit()
    log_action('role', 'edit', '配置角色权限：%s（%d 项）' % (role.name, len(role.permissions)))
    return json_ok(msg='权限保存成功')


def _build_perm_tree(checked_ids=None):
    """构建权限树（供角色授权使用）"""
    checked_ids = set(checked_ids or [])
    perms = AdminPermission.query.order_by(AdminPermission.sort.asc(), AdminPermission.id.asc()).all()
    nodes = {}
    for item in perms:
        nodes[item.id] = {
            'id': item.id,
            'title': item.name,
            'code': item.code,
            'checked': item.id in checked_ids,
            'children': [],
        }
    tree = []
    for item in perms:
        node = nodes[item.id]
        parent = nodes.get(item.parent_id)
        if parent is not None:
            parent['children'].append(node)
        else:
            tree.append(node)
    # layui tree 会将空的 children 数组渲染成可展开节点，这里移除
    for node in nodes.values():
        if not node['children']:
            node.pop('children')
    return tree


# ==================== 权限管理 ====================

@system_bp.route('/permission')
@permission_required('permission:list')
def permission_list():
    return render_template('admin/permission/list.html')


@system_bp.route('/permission/data')
@permission_required('permission:list')
def permission_data():
    items = AdminPermission.query.order_by(AdminPermission.sort.asc(), AdminPermission.id.asc()).all()
    name_map = {item.id: item.name for item in items}
    rows = [{
        'id': item.id,
        'parent_id': item.parent_id,
        'parent_name': name_map.get(item.parent_id, '顶级菜单'),
        'name': item.name,
        'code': item.code,
        'type': item.type,
        'type_text': '菜单' if item.type == 1 else '权限点',
        'icon': item.icon or '',
        'route': item.route or '',
        'sort': item.sort,
        'status': item.status,
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '',
    } for item in items]
    return _table_json(rows, len(rows))


@system_bp.route('/permission/options')
@permission_required('permission:list')
def permission_options():
    """父级菜单下拉数据"""
    items = AdminPermission.query.filter_by(type=1).order_by(
        AdminPermission.sort.asc(), AdminPermission.id.asc()).all()
    return json_ok([{'id': item.id, 'name': item.name} for item in items])


@system_bp.route('/permission/add', methods=['POST'])
@permission_required('permission:add')
def permission_add():
    name = (request.form.get('name') or '').strip()
    code = (request.form.get('code') or '').strip()
    if not name:
        return json_err('请填写权限名称')
    if not code:
        return json_err('请填写权限标识')
    if AdminPermission.query.filter_by(code=code).first():
        return json_err('该权限标识已存在')

    item = AdminPermission(
        name=name[:50],
        code=code[:100],
        parent_id=request.form.get('parent_id', type=int) or 0,
        type=request.form.get('type', 1, type=int) or 1,
        icon=(request.form.get('icon') or '').strip()[:50],
        route=(request.form.get('route') or '').strip()[:100],
        sort=request.form.get('sort', type=int) or 0,
        status=1 if request.form.get('status', '1') == '1' else 0,
    )
    db.session.add(item)
    db.session.commit()
    log_action('permission', 'add', '新增权限：%s' % code)
    return json_ok(msg='新增成功')


@system_bp.route('/permission/edit/<int:pid>', methods=['POST'])
@permission_required('permission:edit')
def permission_edit(pid):
    item = db.session.get(AdminPermission, pid)
    if item is None:
        return json_err('权限不存在')

    name = (request.form.get('name') or '').strip()
    code = (request.form.get('code') or '').strip()
    if not name:
        return json_err('请填写权限名称')
    if not code:
        return json_err('请填写权限标识')
    if AdminPermission.query.filter(AdminPermission.code == code, AdminPermission.id != pid).first():
        return json_err('该权限标识已存在')

    parent_id = request.form.get('parent_id', type=int) or 0
    if parent_id == pid:
        return json_err('父级不能是自己')

    item.name = name[:50]
    item.code = code[:100]
    item.parent_id = parent_id
    item.type = request.form.get('type', 1, type=int) or 1
    item.icon = (request.form.get('icon') or '').strip()[:50]
    item.route = (request.form.get('route') or '').strip()[:100]
    item.sort = request.form.get('sort', type=int) or 0
    item.status = 1 if request.form.get('status', '1') == '1' else 0
    db.session.commit()
    log_action('permission', 'edit', '编辑权限：%s' % code)
    return json_ok(msg='保存成功')


@system_bp.route('/permission/delete/<int:pid>', methods=['POST'])
@permission_required('permission:delete')
def permission_delete(pid):
    item = db.session.get(AdminPermission, pid)
    if item is None:
        return json_err('权限不存在')
    if AdminPermission.query.filter_by(parent_id=pid).count() > 0:
        return json_err('请先删除该权限下的子权限')

    code = item.code
    db.session.delete(item)
    db.session.commit()
    log_action('permission', 'delete', '删除权限：%s' % code)
    return json_ok(msg='删除成功')
