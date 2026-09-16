# -*- coding: utf-8 -*-
"""系统与权限相关模型：管理员、角色、权限、日志"""
from datetime import datetime

from flask import current_app

from app import db


# 管理员-角色 关联表
admin_user_role = db.Table(
    'admin_user_role',
    db.Column('id', db.Integer, primary_key=True, autoincrement=True),
    db.Column('user_id', db.Integer, db.ForeignKey('admin_user.id'), nullable=False, index=True, comment='管理员ID'),
    db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id'), nullable=False, index=True, comment='角色ID'),
    db.UniqueConstraint('user_id', 'role_id', name='uk_user_role'),
    comment='管理员-角色关联表',
)

# 角色-权限 关联表
admin_role_permission = db.Table(
    'admin_role_permission',
    db.Column('id', db.Integer, primary_key=True, autoincrement=True),
    db.Column('role_id', db.Integer, db.ForeignKey('admin_role.id'), nullable=False, index=True, comment='角色ID'),
    db.Column('permission_id', db.Integer, db.ForeignKey('admin_permission.id'), nullable=False, index=True, comment='权限ID'),
    db.UniqueConstraint('role_id', 'permission_id', name='uk_role_permission'),
    comment='角色-权限关联表',
)


class AdminUser(db.Model):
    """管理员"""
    __tablename__ = 'admin_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    username = db.Column(db.String(50), nullable=False, unique=True, comment='登录账号')
    password = db.Column(db.String(255), nullable=False, comment='密码(bcrypt哈希)')
    real_name = db.Column(db.String(50), comment='真实姓名')
    avatar = db.Column(db.String(255), comment='头像URL')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态:1=启用,0=禁用')
    fail_count = db.Column(db.SmallInteger, nullable=False, default=0, comment='连续登录失败次数')
    lock_until = db.Column(db.DateTime, comment='锁定截止时间')
    last_login_at = db.Column(db.DateTime, comment='最后登录时间')
    last_login_ip = db.Column(db.String(50), comment='最后登录IP')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    roles = db.relationship(
        'AdminRole', secondary=admin_user_role, lazy='selectin',
        backref=db.backref('users', lazy='selectin'),
    )

    # ---------------- 密码 ----------------
    def set_password(self, raw):
        import bcrypt
        pwd = raw.encode('utf-8')[:72]
        self.password = bcrypt.hashpw(pwd, bcrypt.gensalt(rounds=12)).decode('utf-8')

    def check_password(self, raw):
        import bcrypt
        try:
            return bcrypt.checkpw(raw.encode('utf-8')[:72], self.password.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    # ---------------- 权限 ----------------
    @property
    def is_super(self):
        """是否为超级管理员（拥有全部权限）"""
        super_id = current_app.config.get('SUPER_ROLE_ID', 1)
        return any(r.id == super_id for r in self.roles)

    def permission_code_set(self):
        """当前用户拥有的权限标识集合（按请求缓存）"""
        from flask import g
        cached = getattr(g, '_perm_code_set', None)
        if cached is not None:
            return cached
        codes = set()
        if not self.is_super:
            for role in self.roles:
                if role.status != 1:
                    continue
                for perm in role.permissions:
                    if perm.status == 1:
                        codes.add(perm.code)
        g._perm_code_set = codes
        return codes

    def has_permission(self, code):
        if self.is_super:
            return True
        return code in self.permission_code_set()

    def role_names(self):
        return '、'.join(r.name for r in self.roles) or '未分配'


class AdminRole(db.Model):
    """角色 / 权限组"""
    __tablename__ = 'admin_role'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    name = db.Column(db.String(50), nullable=False, unique=True, comment='角色名称')
    description = db.Column(db.String(255), comment='角色描述')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态:1=启用,0=禁用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    permissions = db.relationship(
        'AdminPermission', secondary=admin_role_permission, lazy='selectin',
        backref=db.backref('roles', lazy='selectin'),
    )

    @property
    def is_super(self):
        return self.id == current_app.config.get('SUPER_ROLE_ID', 1)


class AdminPermission(db.Model):
    """权限（菜单 + 按钮权限点）"""
    __tablename__ = 'admin_permission'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    parent_id = db.Column(db.Integer, nullable=False, default=0, comment='父级ID(0=顶级菜单)')
    name = db.Column(db.String(50), nullable=False, comment='权限名称')
    code = db.Column(db.String(100), nullable=False, unique=True, comment='权限标识')
    type = db.Column(db.SmallInteger, nullable=False, default=1, comment='类型:1=菜单,2=按钮/权限点')
    icon = db.Column(db.String(50), comment='菜单图标(layui图标类名)')
    route = db.Column(db.String(100), comment='菜单地址')
    sort = db.Column(db.Integer, nullable=False, default=0, comment='排序(越小越前)')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态:1=显示,0=隐藏')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class AdminLog(db.Model):
    """后台操作日志"""
    __tablename__ = 'admin_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, index=True, comment='操作管理员ID')
    username = db.Column(db.String(50), comment='操作账号(冗余)')
    module = db.Column(db.String(50), comment='操作模块')
    action = db.Column(db.String(50), comment='操作类型')
    content = db.Column(db.Text, comment='操作内容描述')
    ip = db.Column(db.String(50), comment='IP地址')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True, comment='操作时间')
