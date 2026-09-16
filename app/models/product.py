# -*- coding: utf-8 -*-
"""业务模型：产品分类、产品"""
import json
from datetime import datetime

from app import db


class ProductCategory(db.Model):
    """产品分类"""
    __tablename__ = 'product_category'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    name = db.Column(db.String(100), nullable=False, comment='分类名称')
    sort = db.Column(db.Integer, nullable=False, default=0, comment='排序(越小越前)')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态:1=启用,0=禁用')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    products = db.relationship('Product', backref='category', lazy='dynamic')


class Product(db.Model):
    """产品"""
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    name = db.Column(db.String(200), nullable=False, comment='产品名称')
    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), index=True, comment='所属分类ID')
    image = db.Column(db.String(500), comment='产品主图URL')
    images = db.Column(db.Text, comment='多图(JSON数组,预留)')
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0, comment='单价(元)')
    unit = db.Column(db.String(20), default='件', comment='计量单位')
    description = db.Column(db.Text, comment='产品描述(富文本,前台暂不展示)')
    spec = db.Column(db.String(255), comment='规格/型号')
    sort = db.Column(db.Integer, nullable=False, default=0, comment='排序(越小越前)')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态:1=上架,0=下架')
    views = db.Column(db.Integer, nullable=False, default=0, comment='浏览量')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    @property
    def image_list(self):
        """多图列表"""
        if not self.images:
            return []
        try:
            data = json.loads(self.images)
            return data if isinstance(data, list) else []
        except (ValueError, TypeError):
            return []

    @property
    def cover(self):
        """封面图：主图优先，其次多图第一张"""
        if self.image:
            return self.image
        imgs = self.image_list
        return imgs[0] if imgs else ''

    @property
    def price_text(self):
        """价格文本，整数不显示小数"""
        value = self.price or 0
        if value == int(value):
            return str(int(value))
        return '%.2f' % value
