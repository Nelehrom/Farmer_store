from app import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # Название
    description = db.Column(db.Text, nullable=True)  # Описание основное
    details = db.Column(db.Text, nullable=True)  # Пищевая/тех инфа

    is_weight_based = db.Column(db.Boolean, default=False)  # Весовой или штучный
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Цена (за кг или шт)

    is_frozen = db.Column(db.Boolean, default=False)  # Замороженный?
    is_discounted = db.Column(db.Boolean, default=False)  # Скидка?

    supplier_name = db.Column(db.String(120), nullable=True)  # Имя поставщика

    image_url = db.Column(db.String(250), nullable=True)  # Картинка
    tags = db.Column(db.String(250), nullable=True)  # Теги, строка

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category', backref='products')

    def __repr__(self):
        return f"<Product {self.name}>"

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    image_url = db.Column(db.String(250), nullable=True)  # картинка категории

    def __repr__(self):
        return f"<Category {self.name}>"
