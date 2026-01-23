from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.forms import RegistrationForm, ProductForm, CategoryForm
from app.models import User, Product, Category
from app.uploads import save_product_image, save_category_image


# -----------------------
# Blueprints
# -----------------------

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
main_bp = Blueprint("main", __name__)


# -----------------------
# Decorators
# -----------------------

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# -----------------------
# Main (public) routes
# -----------------------

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_pw
        )
        db.session.add(user)
        db.session.commit()
        flash("Регистрация прошла успешно! Войдите в аккаунт.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    from app.forms import LoginForm  # локально, чтобы не тащить в импорты если не надо
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Вы вошли в аккаунт!", "success")
            return redirect(url_for("main.profile"))

        flash("Неверный email или пароль", "danger")

    return render_template("login.html", form=form)


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@main_bp.route("/products")
def products():
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("products.html", categories=categories)


@main_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=product)


@main_bp.route("/category/<int:category_id>")
def category_view(category_id):
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category.id).all()
    return render_template("category.html", category=category, products=products)


# -----------------------
# Admin routes
# -----------------------

@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")


# ---- Products CRUD ----

@admin_bp.route("/products")
@admin_required
def admin_products():
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id") or ""

    query = Product.query

    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    if category_id.isdigit():
        query = query.filter(Product.category_id == int(category_id))

    products = query.order_by(Product.id.desc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        "admin/products/index.html",
        products=products,
        categories=categories,
        q=q,
        category_id=category_id
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_create():
    form = ProductForm()

    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(0, "— Без категории —")] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        image_url = ""

        if form.image.data and getattr(form.image.data, "filename", ""):
            try:
                image_url = save_product_image(form.image.data)
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("admin/products/form.html", form=form, mode="create")

        product = Product(
            name=form.name.data,
            description=form.description.data,
            details=form.details.data,
            is_weight_based=form.is_weight_based.data,
            price=form.price.data,
            min_weight=form.min_weight.data,
            max_weight=form.max_weight.data,
            is_frozen=form.is_frozen.data,
            is_discounted=form.is_discounted.data,
            supplier_name=form.supplier_name.data,
            tags=form.tags.data,
            category_id=None if form.category_id.data == 0 else form.category_id.data,
            image_url=image_url or None
        )
        db.session.add(product)
        db.session.commit()
        flash("Товар создан", "success")
        return redirect(url_for("admin.admin_products"))

    return render_template("admin/products/form.html", form=form, mode="create")


@admin_bp.route("/products/<int:product_id>")
@admin_required
def product_view(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("admin/products/view.html", product=product)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)

    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(0, "— Без категории —")] + [(c.id, c.name) for c in categories]
    form.category_id.data = product.category_id or 0

    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.details = form.details.data
        product.is_weight_based = form.is_weight_based.data
        product.price = form.price.data
        product.min_weight = form.min_weight.data
        product.max_weight = form.max_weight.data
        product.is_frozen = form.is_frozen.data
        product.is_discounted = form.is_discounted.data
        product.supplier_name = form.supplier_name.data
        product.tags = form.tags.data
        product.category_id = None if form.category_id.data == 0 else form.category_id.data

        if form.image.data and getattr(form.image.data, "filename", ""):
            try:
                product.image_url = save_product_image(form.image.data)
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("admin/products/form.html", form=form, mode="edit", product=product)

        db.session.commit()
        flash("Товар обновлён", "success")
        return redirect(url_for("admin.product_view", product_id=product.id))

    return render_template("admin/products/form.html", form=form, mode="edit", product=product)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Товар удалён", "info")
    return redirect(url_for("admin.admin_products"))


# ---- Categories CRUD ----

@admin_bp.route("/categories")
@admin_required
def admin_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("admin/categories/index.html", categories=categories)


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@admin_required
def category_create():
    form = CategoryForm()

    if form.validate_on_submit():
        name = form.name.data.strip()

        exists = Category.query.filter(Category.name.ilike(name)).first()
        if exists:
            flash("Категория с таким названием уже существует", "warning")
            return render_template("admin/categories/form.html", form=form, mode="create")

        image_url = ""
        if form.image.data and getattr(form.image.data, "filename", ""):
            try:
                image_url = save_category_image(form.image.data)
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("admin/categories/form.html", form=form, mode="create")

        c = Category(name=name, image_url=image_url or None)
        db.session.add(c)
        db.session.commit()
        flash("Категория создана", "success")
        return redirect(url_for("admin.admin_categories"))

    return render_template("admin/categories/form.html", form=form, mode="create")


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def category_edit(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        name = form.name.data.strip()

        exists = Category.query.filter(Category.name.ilike(name), Category.id != category.id).first()
        if exists:
            flash("Категория с таким названием уже существует", "warning")
            return render_template("admin/categories/form.html", form=form, mode="edit", category=category)

        category.name = name

        if form.image.data and getattr(form.image.data, "filename", ""):
            try:
                category.image_url = save_category_image(form.image.data)
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("admin/categories/form.html", form=form, mode="edit", category=category)

        db.session.commit()
        flash("Категория обновлена", "success")
        return redirect(url_for("admin.admin_categories"))

    return render_template("admin/categories/form.html", form=form, mode="edit", category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def category_delete(category_id):
    category = Category.query.get_or_404(category_id)

    has_products = Product.query.filter_by(category_id=category.id).first() is not None
    if has_products:
        flash("Нельзя удалить категорию: в ней есть товары", "danger")
        return redirect(url_for("admin.admin_categories"))

    db.session.delete(category)
    db.session.commit()
    flash("Категория удалена", "info")
    return redirect(url_for("admin.admin_categories"))
