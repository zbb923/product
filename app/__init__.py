# -*- coding: utf-8 -*-
"""应用工厂"""
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 上传目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # 蓝图注册
    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.product import product_bp
    from app.controllers.system import system_bp
    from app.controllers.front import front_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(front_bp)

    # 请求钩子 / 模板全局变量
    from app.utils.helpers import register_app
    register_app(app)

    # 模板过滤器
    from app.utils.helpers import money, dt

    app.jinja_env.filters['money'] = money
    app.jinja_env.filters['dt'] = dt

    return app
