# -*- coding: utf-8 -*-
"""项目配置"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # ---------------- 基础 ----------------
    SECRET_KEY = os.environ.get('SECRET_KEY', 'product-quote-2026-change-me-in-production')
    SITE_NAME = '产品报价中心'
    SITE_SLOGAN = '产品列表'

    # ---------------- 数据库 ----------------
    # 敏感项一律从环境变量读取，禁止把口令写死在代码/仓库里
    MYSQL_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('DB_PORT', '3306'))
    MYSQL_USER = os.environ.get('DB_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', '')
    MYSQL_DB = os.environ.get('DB_NAME', 'product_quote')
    MYSQL_CHARSET = os.environ.get('DB_CHARSET', 'utf8mb4')

    SQLALCHEMY_DATABASE_URI = (
        'mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset={charset}'.format(
            user=MYSQL_USER, pwd=MYSQL_PASSWORD, host=MYSQL_HOST,
            port=MYSQL_PORT, db=MYSQL_DB, charset=MYSQL_CHARSET,
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 3600}

    # ---------------- 上传 ----------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'product')
    UPLOAD_URL_PREFIX = '/static/uploads/product'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024          # 单文件最大 10MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

    # ---------------- 登录安全 ----------------
    LOGIN_MAX_FAIL = 5                              # 连续失败上限
    LOGIN_LOCK_MINUTES = 15                         # 锁定时长(分钟)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 7200               # 会话 2 小时

    # ---------------- 分页 ----------------
    PAGE_SIZE_ADMIN = 15
    PAGE_SIZE_FRONT = 12

    # 超级管理员角色 ID（该角色拥有全部权限，且不可删除）
    SUPER_ROLE_ID = 1
