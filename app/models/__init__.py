# -*- coding: utf-8 -*-
"""模型统一出口"""
from app.models.system import (  # noqa: F401
    AdminUser,
    AdminRole,
    AdminPermission,
    AdminLog,
    admin_user_role,
    admin_role_permission,
)
from app.models.product import Product, ProductCategory  # noqa: F401

__all__ = [
    'AdminUser', 'AdminRole', 'AdminPermission', 'AdminLog',
    'admin_user_role', 'admin_role_permission',
    'Product', 'ProductCategory',
]
