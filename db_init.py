# -*- coding: utf-8 -*-
"""数据库初始化脚本（可重复执行，不会覆盖已有数据）

用法：python db_init.py
"""
import sys

import pymysql
from decimal import Decimal

from config import Config


def create_database():
    """创建数据库（不存在时）"""
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        charset=Config.MYSQL_CHARSET,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                'CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8mb4 '
                'COLLATE utf8mb4_general_ci' % Config.MYSQL_DB
            )
        conn.commit()
    finally:
        conn.close()
    print('[1/4] 数据库 `%s` 已就绪' % Config.MYSQL_DB)


# (id, parent_id, 名称, 权限标识, 类型 1=菜单 2=权限点, 图标, 地址, 排序)
PERMISSIONS = [
    (1, 0, '控制台', 'dashboard', 1, 'layui-icon-home', '/admin/', 10),

    (2, 0, '产品管理', 'product', 1, 'layui-icon-app', '/admin/product', 20),
    (21, 2, '查看产品', 'product:list', 2, None, '', 21),
    (22, 2, '新增产品', 'product:add', 2, None, '', 22),
    (23, 2, '编辑产品', 'product:edit', 2, None, '', 23),
    (24, 2, '删除产品', 'product:delete', 2, None, '', 24),

    (3, 0, '分类管理', 'category', 1, 'layui-icon-template-1', '/admin/category', 30),
    (31, 3, '查看分类', 'category:list', 2, None, '', 31),
    (32, 3, '新增分类', 'category:add', 2, None, '', 32),
    (33, 3, '编辑分类', 'category:edit', 2, None, '', 33),
    (34, 3, '删除分类', 'category:delete', 2, None, '', 34),

    (4, 0, '管理员管理', 'user', 1, 'layui-icon-username', '/admin/user', 40),
    (41, 4, '查看管理员', 'user:list', 2, None, '', 41),
    (42, 4, '新增管理员', 'user:add', 2, None, '', 42),
    (43, 4, '编辑管理员', 'user:edit', 2, None, '', 43),
    (44, 4, '删除管理员', 'user:delete', 2, None, '', 44),

    (5, 0, '角色管理', 'role', 1, 'layui-icon-group', '/admin/role', 50),
    (51, 5, '查看角色', 'role:list', 2, None, '', 51),
    (52, 5, '新增角色', 'role:add', 2, None, '', 52),
    (53, 5, '编辑角色', 'role:edit', 2, None, '', 53),
    (54, 5, '删除角色', 'role:delete', 2, None, '', 54),

    (6, 0, '权限管理', 'permission', 1, 'layui-icon-vercode', '/admin/permission', 60),
    (61, 6, '查看权限', 'permission:list', 2, None, '', 61),
    (62, 6, '新增权限', 'permission:add', 2, None, '', 62),
    (63, 6, '编辑权限', 'permission:edit', 2, None, '', 63),
    (64, 6, '删除权限', 'permission:delete', 2, None, '', 64),

    (7, 0, '操作日志', 'log', 1, 'layui-icon-log', '/admin/log', 70),
    (71, 7, '查看日志', 'log:list', 2, None, '', 71),

    (8, 0, '个人中心', 'profile', 1, 'layui-icon-account', '/admin/profile', 90),
]

# 运营角色默认拥有的权限标识
OPERATOR_PERMISSIONS = [
    'dashboard',
    'product', 'product:list', 'product:add', 'product:edit', 'product:delete',
    'category', 'category:list', 'category:add', 'category:edit', 'category:delete',
    'profile',
]

DEMO_CATEGORIES = ['办公用品', '电子配件', '包装耗材']

DEMO_PRODUCTS = [
    ('A4 复印纸 70g', 0, '500 张/包', '包', Decimal('23.50')),
    ('中性签字笔 0.5mm', 0, '12 支/盒', '盒', Decimal('18.00')),
    ('USB-C 数据线 1m', 1, '3A 快充', '条', Decimal('12.90')),
    ('65W 氮化镓充电器', 1, '双 C 口', '个', Decimal('129.00')),
    ('气泡信封袋 20x30', 2, '100 个/捆', '捆', Decimal('35.00')),
    ('透明封箱胶带', 2, '宽 4.5cm x 100m', '卷', Decimal('6.80')),
]


def seed_permissions(db, AdminPermission):
    created = 0
    for pid, parent_id, name, code, ptype, icon, route, sort in PERMISSIONS:
        exists = db.session.get(AdminPermission, pid)
        if exists:
            continue
        db.session.add(AdminPermission(
            id=pid, parent_id=parent_id, name=name, code=code, type=ptype,
            icon=icon, route=route, sort=sort, status=1,
        ))
        created += 1
    db.session.commit()
    print('[2/4] 权限数据：新增 %d 条，共 %d 条' % (created, len(PERMISSIONS)))


def seed_roles_and_users(db, AdminRole, AdminUser, AdminPermission):
    super_role_id = Config.SUPER_ROLE_ID

    # 超级管理员角色（拥有全部权限）
    super_role = db.session.get(AdminRole, super_role_id)
    if super_role is None:
        super_role = AdminRole(id=super_role_id, name='超级管理员',
                               description='拥有系统全部权限，不可删除', status=1)
        db.session.add(super_role)
    super_role.permissions = AdminPermission.query.all()

    # 运营角色（示例权限组）
    operator_role = AdminRole.query.filter_by(name='运营').first()
    if operator_role is None:
        operator_role = AdminRole(name='运营', description='可管理产品与分类，无系统管理权限', status=1)
        db.session.add(operator_role)
        db.session.flush()
    operator_role.permissions = AdminPermission.query.filter(
        AdminPermission.code.in_(OPERATOR_PERMISSIONS)).all()

    db.session.commit()

    # 超级管理员账号
    if AdminUser.query.filter_by(username='admin').first() is None:
        admin = AdminUser(username='admin', real_name='超级管理员', status=1)
        admin.set_password('admin123')
        admin.roles = [super_role]
        db.session.add(admin)
        print('      已创建超级管理员账号：admin / admin123')

    # 运营演示账号
    if AdminUser.query.filter_by(username='yunying').first() is None:
        op = AdminUser(username='yunying', real_name='运营小张', status=1)
        op.set_password('yunying123')
        op.roles = [operator_role]
        db.session.add(op)
        print('      已创建运营演示账号：yunying / yunying123')

    db.session.commit()
    print('[3/4] 角色与账号已就绪（超级管理员 + 运营）')


def seed_demo_products(db, Product, ProductCategory):
    if Product.query.count() > 0:
        print('[4/4] 已存在产品数据，跳过演示数据写入')
        return

    cat_map = {}
    for index, name in enumerate(DEMO_CATEGORIES):
        cat = ProductCategory.query.filter_by(name=name).first()
        if cat is None:
            cat = ProductCategory(name=name, sort=(index + 1) * 10, status=1)
            db.session.add(cat)
            db.session.flush()
        cat_map[index] = cat.id
    db.session.commit()

    for index, (name, cat_index, spec, unit, price) in enumerate(DEMO_PRODUCTS):
        db.session.add(Product(
            name=name,
            category_id=cat_map.get(cat_index),
            spec=spec,
            unit=unit,
            price=price,
            sort=(index + 1) * 10,
            status=1,
        ))
    db.session.commit()
    print('[4/4] 已写入 %d 个演示分类、%d 个演示产品（图片可在后台上传）'
          % (len(DEMO_CATEGORIES), len(DEMO_PRODUCTS)))


def main():
    try:
        create_database()
    except pymysql.err.OperationalError as exc:
        print('无法连接 MySQL：%s' % exc)
        print('请检查 config.py 中的数据库地址、账号、密码是否正确，以及 MySQL 服务是否已启动。')
        sys.exit(1)

    from app import create_app, db
    from app.models import AdminPermission, AdminRole, AdminUser, Product, ProductCategory

    app = create_app()
    with app.app_context():
        db.create_all()
        seed_permissions(db, AdminPermission)
        seed_roles_and_users(db, AdminRole, AdminUser, AdminPermission)
        seed_demo_products(db, Product, ProductCategory)

    print('')
    print('=' * 58)
    print(' 初始化完成！启动服务：python run.py')
    print(' 后台地址：http://127.0.0.1:5000/admin/login')
    print(' 超管账号：admin    / admin123')
    print(' 运营账号：yunying  / yunying123')
    print('=' * 58)


if __name__ == '__main__':
    main()
