# -*- coding: utf-8 -*-
"""图片上传处理"""
import os
import uuid
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def save_image(file_storage):
    """保存上传图片，返回可直接访问的 URL；失败抛出 ValueError"""
    if file_storage is None or not file_storage.filename:
        raise ValueError('请选择要上传的文件')

    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename):
        allow = '、'.join(sorted(current_app.config['ALLOWED_EXTENSIONS']))
        raise ValueError('仅支持 %s 格式的图片' % allow)

    ext = filename.rsplit('.', 1)[1].lower()
    # 按天分目录，避免单目录文件过多
    sub_dir = datetime.now().strftime('%Y%m')
    save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], sub_dir)
    os.makedirs(save_dir, exist_ok=True)

    new_name = '%s.%s' % (uuid.uuid4().hex, ext)
    file_storage.save(os.path.join(save_dir, new_name))

    return '%s/%s/%s' % (current_app.config['UPLOAD_URL_PREFIX'], sub_dir, new_name)


def delete_image(url):
    """删除本地图片（仅处理本地上传目录内的文件）"""
    if not url:
        return
    prefix = current_app.config['UPLOAD_URL_PREFIX']
    if not url.startswith(prefix):
        return
    relative = url[len(prefix):].lstrip('/')
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative.replace('/', os.sep))
    path = os.path.normpath(path)
    root = os.path.normpath(current_app.config['UPLOAD_FOLDER'])
    if path.startswith(root) and os.path.isfile(path):
        os.remove(path)
