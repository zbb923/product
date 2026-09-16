# -*- coding: utf-8 -*-
"""启动入口

首次运行请先执行：python db_init.py
启动服务：      python run.py
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print(' * 前台首页 : http://127.0.0.1:5000/')
    print(' * 后台入口 : http://127.0.0.1:5000/admin/login')
    app.run(host='0.0.0.0', port=5000, debug=True)
