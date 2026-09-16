# -*- coding: utf-8 -*-
"""产品管理、分类管理、图片上传"""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, render_template, request

from app import db
from app.models import Product, ProductCategory
from app.utils.decorators import login_required, permission_required
from app.utils.helpers import json_err, json_ok, log_action
from app.utils.upload import delete_image, save_image

product_bp = Blueprint('product', __name__, url_prefix='/admin')


def _table_json(items, total, msg=''):
    """layui table 数据格式"""
    return jsonify({'code': 0, 'msg': msg, 'count': total, 'data': items})


# ==================== 图片上传 ====================

@product_bp.route('/upload/image', methods=['POST'])
@login_required
def upload_image():
    file = request.files.get('file') or request.files.get('image')
    try:
        url = save_image(file)
    except ValueError as exc:
        return json_err(str(exc), code=400)
    except Exception as exc:  # noqa: BLE001
        return json_err('上传失败：%s' % exc, code=500)
    return jsonify({'code': 0, 'msg': '上传成功', 'data': {'src': url, 'url': url}})


# ==================== 产品管理 ====================

@product_bp.route('/product')
@permission_required('product:list')
def product_list():
    categories = ProductCategory.query.filter_by(status=1).order_by(
        ProductCategory.sort.asc(), ProductCategory.id.asc()).all()
    return render_template('admin/product/list.html', categories=categories)


@product_bp.route('/product/data')
@permission_required('product:list')
def product_data():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('limit', 15, type=int)
    keyword = (request.args.get('keyword') or '').strip()
    category_id = request.args.get('category_id', type=int)
    status = request.args.get('status', type=int)

    query = Product.query
    if keyword:
        query = query.filter(db.or_(
            Product.name.like('%%%s%%' % keyword),
            Product.spec.like('%%%s%%' % keyword),
        ))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status is not None and status in (0, 1):
        query = query.filter(Product.status == status)

    pagination = query.order_by(Product.sort.asc(), Product.id.desc()).paginate(
        page=page, per_page=size, error_out=False)

    rows = []
    for item in pagination.items:
        rows.append({
            'id': item.id,
            'name': item.name,
            'category_name': item.category.name if item.category else '未分类',
            'image': item.cover,
            'price': item.price_text,
            'unit': item.unit or '',
            'spec': item.spec or '',
            'sort': item.sort,
            'status': item.status,
            'views': item.views,
            'updated_at': item.updated_at.strftime('%Y-%m-%d %H:%M') if item.updated_at else '',
        })
    return _table_json(rows, pagination.total)


@product_bp.route('/product/add', methods=['GET', 'POST'])
@permission_required('product:add')
def product_add():
    if request.method == 'GET':
        categories = ProductCategory.query.order_by(
            ProductCategory.sort.asc(), ProductCategory.id.asc()).all()
        return render_template('admin/product/form.html', product=None, categories=categories)

    data, error = _read_product_form()
    if error:
        return json_err(error)
    item = Product(**data)
    db.session.add(item)
    db.session.commit()
    log_action('product', 'add', '新增产品：%s' % item.name)
    return json_ok({'redirect': '/admin/product'}, '新增成功')


@product_bp.route('/product/edit/<int:pid>', methods=['GET', 'POST'])
@permission_required('product:edit')
def product_edit(pid):
    item = db.session.get(Product, pid)
    if item is None:
        if request.method == 'GET':
            return '产品不存在', 404
        return json_err('产品不存在')

    if request.method == 'GET':
        categories = ProductCategory.query.order_by(
            ProductCategory.sort.asc(), ProductCategory.id.asc()).all()
        return render_template('admin/product/form.html', product=item, categories=categories)

    data, error = _read_product_form()
    if error:
        return json_err(error)

    old_image = item.image
    for key, value in data.items():
        setattr(item, key, value)
    db.session.commit()
    if old_image and old_image != item.image:
        delete_image(old_image)
    log_action('product', 'edit', '编辑产品：%s' % item.name)
    return json_ok({'redirect': '/admin/product'}, '保存成功')


@product_bp.route('/product/delete/<int:pid>', methods=['POST'])
@permission_required('product:delete')
def product_delete(pid):
    item = db.session.get(Product, pid)
    if item is None:
        return json_err('产品不存在')
    name, image = item.name, item.image
    db.session.delete(item)
    db.session.commit()
    delete_image(image)
    log_action('product', 'delete', '删除产品：%s' % name)
    return json_ok(msg='删除成功')


@product_bp.route('/product/toggle/<int:pid>', methods=['POST'])
@permission_required('product:edit')
def product_toggle(pid):
    item = db.session.get(Product, pid)
    if item is None:
        return json_err('产品不存在')
    item.status = 0 if item.status == 1 else 1
    db.session.commit()
    log_action('product', 'edit', '%s产品：%s' % ('上架' if item.status == 1 else '下架', item.name))
    return json_ok({'status': item.status}, '操作成功')


@product_bp.route('/product/sort', methods=['POST'])
@permission_required('product:edit')
def product_sort():
    pid = request.form.get('id', type=int)
    sort = request.form.get('sort', type=int)
    if pid is None or sort is None:
        return json_err('参数错误')
    item = db.session.get(Product, pid)
    if item is None:
        return json_err('产品不存在')
    item.sort = sort
    db.session.commit()
    log_action('product', 'edit', '调整排序：%s → %d' % (item.name, sort))
    return json_ok(msg='排序已更新')


def _read_product_form():
    """读取并校验产品表单，返回 (数据字典, 错误信息)"""
    name = (request.form.get('name') or '').strip()
    if not name:
        return None, '请填写产品名称'
    if len(name) > 200:
        return None, '产品名称不能超过 200 个字符'

    price_raw = (request.form.get('price') or '0').strip()
    try:
        price = Decimal(price_raw)
    except (InvalidOperation, ValueError):
        return None, '单价必须是数字'
    if price < 0:
        return None, '单价不能为负数'
    if price > Decimal('99999999.99'):
        return None, '单价超出可填写范围'

    category_id = request.form.get('category_id', type=int) or None
    if category_id and db.session.get(ProductCategory, category_id) is None:
        return None, '所选分类不存在'

    spec = (request.form.get('spec') or '').strip()
    if len(spec) > 255:
        return None, '规格/型号不能超过 255 个字符'

    unit = (request.form.get('unit') or '').strip() or '件'
    if len(unit) > 20:
        return None, '计量单位不能超过 20 个字符'

    return {
        'name': name,
        'category_id': category_id,
        'image': (request.form.get('image') or '').strip(),
        'price': price,
        'unit': unit,
        'spec': spec,
        'description': request.form.get('description') or '',
        'sort': request.form.get('sort', type=int) or 0,
        'status': 1 if request.form.get('status', '1') == '1' else 0,
    }, None


# ==================== 分类管理 ====================

@product_bp.route('/category')
@permission_required('category:list')
def category_list():
    return render_template('admin/category/list.html')


@product_bp.route('/category/data')
@permission_required('category:list')
def category_data():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('limit', 15, type=int)
    keyword = (request.args.get('keyword') or '').strip()

    query = ProductCategory.query
    if keyword:
        query = query.filter(ProductCategory.name.like('%%%s%%' % keyword))

    pagination = query.order_by(ProductCategory.sort.asc(), ProductCategory.id.asc()).paginate(
        page=page, per_page=size, error_out=False)

    rows = [{
        'id': item.id,
        'name': item.name,
        'sort': item.sort,
        'status': item.status,
        'product_count': item.products.count(),
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else '',
    } for item in pagination.items]
    return _table_json(rows, pagination.total)


@product_bp.route('/category/add', methods=['POST'])
@permission_required('category:add')
def category_add():
    name = (request.form.get('name') or '').strip()
    if not name:
        return json_err('请填写分类名称')
    if len(name) > 100:
        return json_err('分类名称不能超过 100 个字符')
    if ProductCategory.query.filter_by(name=name).first():
        return json_err('该分类名称已存在')

    item = ProductCategory(
        name=name,
        sort=request.form.get('sort', type=int) or 0,
        status=1 if request.form.get('status', '1') == '1' else 0,
    )
    db.session.add(item)
    db.session.commit()
    log_action('category', 'add', '新增分类：%s' % name)
    return json_ok(msg='新增成功')


@product_bp.route('/category/edit/<int:cid>', methods=['POST'])
@permission_required('category:edit')
def category_edit(cid):
    item = db.session.get(ProductCategory, cid)
    if item is None:
        return json_err('分类不存在')

    name = (request.form.get('name') or '').strip()
    if not name:
        return json_err('请填写分类名称')
    if len(name) > 100:
        return json_err('分类名称不能超过 100 个字符')
    exists = ProductCategory.query.filter(ProductCategory.name == name, ProductCategory.id != cid).first()
    if exists:
        return json_err('该分类名称已存在')

    item.name = name
    item.sort = request.form.get('sort', type=int) or 0
    item.status = 1 if request.form.get('status', '1') == '1' else 0
    db.session.commit()
    log_action('category', 'edit', '编辑分类：%s' % name)
    return json_ok(msg='保存成功')


@product_bp.route('/category/delete/<int:cid>', methods=['POST'])
@permission_required('category:delete')
def category_delete(cid):
    item = db.session.get(ProductCategory, cid)
    if item is None:
        return json_err('分类不存在')
    if item.products.count() > 0:
        return json_err('该分类下还有产品，无法删除')
    name = item.name
    db.session.delete(item)
    db.session.commit()
    log_action('category', 'delete', '删除分类：%s' % name)
    return json_ok(msg='删除成功')
