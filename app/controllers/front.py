# -*- coding: utf-8 -*-
"""前台展示：产品列表、产品详情"""
from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, render_template, request

from app import db
from app.models import Product, ProductCategory
from app.utils.helpers import json_err

front_bp = Blueprint('front', __name__)


def _visible_categories():
    return ProductCategory.query.filter_by(status=1).order_by(
        ProductCategory.sort.asc(), ProductCategory.id.asc()).all()


@front_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    keyword = (request.args.get('keyword') or '').strip()
    size = current_app.config['PAGE_SIZE_FRONT']

    query = Product.query.filter_by(status=1)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(db.or_(
            Product.name.like('%%%s%%' % keyword),
            Product.spec.like('%%%s%%' % keyword),
        ))

    pagination = query.order_by(Product.sort.asc(), Product.id.desc()).paginate(
        page=page, per_page=size, error_out=False)

    # 分页链接参数（保留筛选条件）
    args = {}
    if category_id:
        args['category'] = category_id
    if keyword:
        args['keyword'] = keyword

    return render_template(
        'front/index.html',
        products=pagination.items,
        pagination=pagination,
        categories=_visible_categories(),
        current_category=category_id,
        keyword=keyword,
        base_query=urlencode(args),
    )


@front_bp.route('/product/<int:pid>')
def detail(pid):
    item = db.session.get(Product, pid)
    if item is None or item.status != 1:
        return render_template('front/404.html'), 404

    item.views = (item.views or 0) + 1
    db.session.commit()

    related = Product.query.filter(
        Product.status == 1, Product.id != item.id,
        Product.category_id == item.category_id,
    ).order_by(Product.sort.asc(), Product.id.desc()).limit(4).all()

    if not related:
        related = Product.query.filter(
            Product.status == 1, Product.id != item.id,
        ).order_by(Product.sort.asc(), Product.id.desc()).limit(4).all()

    return render_template('front/detail.html', product=item, related=related,
                           categories=_visible_categories())


@front_bp.route('/api/products')
def api_products():
    """前台产品列表 JSON 接口"""
    page = request.args.get('page', 1, type=int)
    size = min(request.args.get('size', current_app.config['PAGE_SIZE_FRONT'], type=int), 50)
    category_id = request.args.get('category', type=int)
    keyword = (request.args.get('keyword') or '').strip()

    query = Product.query.filter_by(status=1)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(db.or_(
            Product.name.like('%%%s%%' % keyword),
            Product.spec.like('%%%s%%' % keyword),
        ))

    pagination = query.order_by(Product.sort.asc(), Product.id.desc()).paginate(
        page=page, per_page=size, error_out=False)

    items = [{
        'id': item.id,
        'name': item.name,
        'image': item.cover,
        'price': item.price_text,
        'unit': item.unit or '',
        'spec': item.spec or '',
        'category_id': item.category_id,
        'category_name': item.category.name if item.category else '',
    } for item in pagination.items]

    return jsonify({
        'code': 0,
        'msg': '',
        'data': {
            'items': items,
            'total': pagination.total,
            'page': pagination.page,
            'pages': pagination.pages,
        },
    })


@front_bp.route('/api/product/<int:pid>')
def api_product(pid):
    item = db.session.get(Product, pid)
    if item is None or item.status != 1:
        return json_err('产品不存在', code=404)
    return jsonify({
        'code': 0,
        'msg': '',
        'data': {
            'id': item.id,
            'name': item.name,
            'image': item.cover,
            'images': item.image_list,
            'price': item.price_text,
            'unit': item.unit or '',
            'spec': item.spec or '',
            'category_id': item.category_id,
            'category_name': item.category.name if item.category else '',
        },
    })
