from datetime import date, timedelta
from app import db
from flask_login import UserMixin
from decimal import Decimal

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Preorder(db.Model):
    __tablename__ = "preorders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    user = db.relationship("User", backref=db.backref("preorders", lazy=True))

    comment = db.Column(db.Text, nullable=True)
    pickup_time = db.Column(db.String(5), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    items = db.relationship(
        "PreorderItem",
        backref="preorder",
        lazy=True,
        cascade="all, delete-orphan"
    )


class PreorderItem(db.Model):
    __tablename__ = "preorder_items"

    id = db.Column(db.Integer, primary_key=True)
    preorder_id = db.Column(db.Integer, db.ForeignKey("preorders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    product = db.relationship("Product", backref=db.backref("preorder_items", lazy=True))

    quantity = db.Column(db.Numeric(10, 3), nullable=False)


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)

    is_weight_based = db.Column(db.Boolean, default=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    is_frozen = db.Column(db.Boolean, default=False)
    is_discounted = db.Column(db.Boolean, default=False)

    supplier_name = db.Column(db.String(120), nullable=True)

    image_url = db.Column(db.String(250), nullable=True)
    tags = db.Column(db.String(250), nullable=True)

    # ✅ Срок годности как "N дней"
    shelf_life_days = db.Column(db.Integer, nullable=False, default=7)
    db.CheckConstraint('shelf_life_days > 0', name='ck_products_shelf_life_days_pos')

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category', backref=db.backref('products', lazy=True))

    def __repr__(self):
        return f"<Product {self.name}>"


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    image_url = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f"<Category {self.name}>"


# ✅ Партия/склад
class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    expires_at = db.Column(db.Date, nullable=False, index=True)
    product = db.relationship("Product", backref=db.backref("batches", lazy=True, cascade="all, delete-orphan"))

    quantity = db.Column(db.Numeric(10, 3), nullable=False)  # и для кг, и для штук (просто число)
    db.CheckConstraint('quantity > 0', name='ck_batches_quantity_pos')
    produced_at = db.Column(db.Date, nullable=False, default=date.today)
    expires_at = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __repr__(self):
        return f"<Batch {self.id} product={self.product_id} qty={self.quantity} exp={self.expires_at}>"

    @staticmethod
    def calc_expires(produced_at: date, shelf_life_days: int) -> date:
        return produced_at + timedelta(days=int(shelf_life_days))



class WriteOff(db.Model):
    __tablename__ = "write_offs"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    product = db.relationship("Product", backref=db.backref("write_offs", lazy=True))

    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<WriteOff {self.id} product={self.product_id} qty={self.quantity}>"

class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    items = db.relationship(
        "SaleItem",
        backref="sale",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def total_amount(self):
        return sum((Decimal(str(item.line_total)) for item in self.items), Decimal("0.00"))


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)

    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    product = db.relationship("Product", backref=db.backref("sale_items", lazy=True))

    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    source_produced_at = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<SaleItem {self.id} sale={self.sale_id} product={self.product_id} qty={self.quantity}>"
