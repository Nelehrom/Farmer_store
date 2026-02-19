from functools import wraps
from datetime import date, timedelta
from decimal import Decimal

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort, session
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.forms import (
    RegistrationForm, ProductForm, CategoryForm,
    SupplySearchForm, SupplyAddLineForm,
    SalesAddLineForm, SalesHistoryFilterForm

)
from app.models import User, Product, Category, Batch, WriteOff, Sale, SaleItem
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
# Supply helpers (session draft)
# -----------------------
def _supply_lines():
    # list[dict]: {product_id:int, qty:str, produced_at:str(YYYY-MM-DD)}
    return session.get("supply_lines", [])

def _save_supply_lines(lines):
    session["supply_lines"] = lines
    session.modified = True

def _clear_supply_lines():
    session.pop("supply_lines", None)
    session.modified = True

def _sales_lines():
    # list[dict]: {product_id:int, qty:str}
    return session.get("sales_lines", [])


def _save_sales_lines(lines):
    session["sales_lines"] = lines
    session.modified = True


def _clear_sales_lines():
    session.pop("sales_lines", None)
    session.modified = True


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
    from app.forms import LoginForm
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
            image_url=image_url or None,
            # ✅ новое поле
            shelf_life_days=form.shelf_life_days.data
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
        # ✅ новое поле
        product.shelf_life_days = form.shelf_life_days.data

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


# -----------------------
# ✅ Supply (Поставка)
# -----------------------
@admin_bp.route("/supply", methods=["GET"])
@admin_required
def admin_supply():
    q = (request.args.get("q") or "").strip()
    products = []

    if q:
        products = (
            Product.query
            .filter(Product.name.ilike(f"%{q}%"))
            .order_by(Product.name.asc())
            .limit(25)
            .all()
        )

    lines = _supply_lines()

    # подгрузим товары для отображения списка (названия/тип)
    product_map = {}
    if lines:
        ids = [int(x["product_id"]) for x in lines]
        product_map = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()}

    add_form = SupplyAddLineForm()  # для формы "добавить позицию" в карточке товара

    return render_template(
        "admin/supply/index.html",
        q=q,
        products=products,
        lines=lines,
        product_map=product_map,
        add_form=add_form
    )


@admin_bp.route("/supply/add", methods=["POST"])
@admin_required
def admin_supply_add():
    form = SupplyAddLineForm()

    if not request.form.get("product_id"):
        flash("Сначала выбери товар в поиске", "warning")
        return redirect(url_for("admin.admin_supply", q=request.form.get("q", "")))

    if not form.validate_on_submit():
        flash("Заполни количество (и дату изготовления при необходимости)", "danger")
        return redirect(url_for("admin.admin_supply"))

    product = Product.query.get_or_404(form.product_id.data)

    produced_at = form.produced_at.data or date.today()
    qty = form.quantity.data

    # На всякий: Decimal
    try:
        qty = Decimal(str(qty))
    except Exception:
        flash("Некорректное количество", "danger")
        return redirect(url_for("admin.admin_supply"))

    if qty <= 0:
        flash("Количество должно быть больше 0", "danger")
        return redirect(url_for("admin.admin_supply"))

    lines = _supply_lines()

    # если уже есть такая же позиция (тот же товар + та же дата изготовления) — просто суммируем
    key_prod = int(product.id)
    key_date = produced_at.isoformat()

    merged = False
    for line in lines:
        if int(line["product_id"]) == key_prod and line.get("produced_at") == key_date:
            line["qty"] = str(Decimal(line["qty"]) + qty)
            merged = True
            break

    if not merged:
        lines.append({
            "product_id": key_prod,
            "qty": str(qty),
            "produced_at": key_date
        })

    _save_supply_lines(lines)
    flash(f"Добавлено в поставку: {product.name}", "success")
    return redirect(url_for("admin.admin_supply", q=request.form.get("q", "")))


@admin_bp.route("/supply/remove/<int:idx>", methods=["POST"])
@admin_required
def admin_supply_remove(idx):
    lines = _supply_lines()
    if 0 <= idx < len(lines):
        lines.pop(idx)
        _save_supply_lines(lines)
        flash("Позиция удалена из поставки", "info")
    return redirect(url_for("admin.admin_supply"))


@admin_bp.route("/supply/clear", methods=["POST"])
@admin_required
def admin_supply_clear():
    _clear_supply_lines()
    flash("Список поставки очищен", "info")
    return redirect(url_for("admin.admin_supply"))


@admin_bp.route("/supply/confirm", methods=["POST"])
@admin_required
def admin_supply_confirm():
    lines = _supply_lines()
    if not lines:
        flash("Список поставки пуст", "warning")
        return redirect(url_for("admin.admin_supply"))

    # создаём партии
    for line in lines:
        product = Product.query.get(int(line["product_id"]))
        if not product:
            continue

        produced_at = date.fromisoformat(line["produced_at"])
        expires_at = Batch.calc_expires(produced_at, product.shelf_life_days)
        qty = Decimal(line["qty"])

        b = Batch(
            product_id=product.id,
            quantity=qty,
            produced_at=produced_at,
            expires_at=expires_at
        )
        db.session.add(b)

    db.session.commit()
    _clear_supply_lines()
    flash("Поставка подтверждена: партии добавлены на склад", "success")
    return redirect(url_for("admin.admin_batches"))


# -----------------------
# ✅ Batches (Склад)
# -----------------------
@admin_bp.route("/batches")
@admin_required
def admin_batches():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()  # "", "active", "expiring", "expired"
    days = request.args.get("days", "3")

    try:
        days_int = int(days)
    except Exception:
        days_int = 3

    today = date.today()
    soon_border = today + timedelta(days=days_int)

    query = Batch.query.join(Product)

    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))


    if status == "expired":
        query = query.filter(Batch.expires_at < today)
    elif status == "expiring":
        query = query.filter(Batch.expires_at >= today, Batch.expires_at <= soon_border)
    elif status == "active":
        query = query.filter(Batch.expires_at > soon_border)

    batches = query.order_by(Batch.expires_at.asc(), Batch.id.desc()).all()

    for batch in batches:
        if batch.expires_at < today:
            batch._status = "expired"
        elif batch.expires_at <= soon_border:
            batch._status = "expiring"
        else:
            batch._status = "active"

        qty = Decimal(str(batch.quantity))
        if batch.product.is_weight_based:
            batch._qty_display = format(qty.normalize(), "f").rstrip("0").rstrip(".")
        else:
            batch._qty_display = str(int(qty))


    return render_template(
        "admin/batches/index.html",
        batches=batches,
        status=status,
        days=days_int,
        today=today,
        soon_border=soon_border
    )


@admin_bp.route("/batches/<int:batch_id>/writeoff", methods=["POST"])
@admin_required
def admin_batch_writeoff(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    reason = (request.form.get("reason") or "").strip()

    if not reason:
        flash("Укажите причину списания", "danger")
        return redirect(url_for("admin.admin_batches"))

    entry = WriteOff(
        product_id=batch.product_id,
        quantity=batch.quantity,
        reason=reason
    )

    db.session.add(entry)
    db.session.delete(batch)
    db.session.commit()

    flash("Партия списана и сохранена в журнале списаний", "success")
    return redirect(url_for("admin.admin_batches"))


# -----------------------
# ✅ Sales (Продажи)
# -----------------------
@admin_bp.route("/sales", methods=["GET"])
@admin_required
def admin_sales():
    q = (request.args.get("q") or "").strip()
    products = []

    if q:
        products = (
            Product.query
            .filter(Product.name.ilike(f"%{q}%"))
            .order_by(Product.name.asc())
            .limit(25)
            .all()
        )

    lines = _sales_lines()
    product_map = {}
    available_map = {}

    if lines:
        ids = [int(x["product_id"]) for x in lines]
        product_map = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()}

    today = date.today()
    all_products = Product.query.all()
    for product in all_products:
        available_qty = (
            db.session.query(db.func.coalesce(db.func.sum(Batch.quantity), 0))
            .filter(Batch.product_id == product.id, Batch.expires_at >= today)
            .scalar()
        )
        available_map[product.id] = Decimal(str(available_qty or 0))

    add_form = SalesAddLineForm()

    line_total_sum = Decimal("0.00")
    for line in lines:
        product = product_map.get(int(line["product_id"]))
        if not product:
            continue
        qty = Decimal(line["qty"])
        line_total_sum += qty * Decimal(str(product.price))

    return render_template(
        "admin/sales/index.html",
        q=q,
        products=products,
        lines=lines,
        product_map=product_map,
        available_map=available_map,
        add_form=add_form,
        line_total_sum=line_total_sum
    )


@admin_bp.route("/sales/add", methods=["POST"])
@admin_required
def admin_sales_add():
    form = SalesAddLineForm()

    if not request.form.get("product_id"):
        flash("Сначала выбери товар в поиске", "warning")
        return redirect(url_for("admin.admin_sales", q=request.form.get("q", "")))

    if not form.validate_on_submit():
        flash("Заполни корректное количество", "danger")
        return redirect(url_for("admin.admin_sales"))

    product = Product.query.get_or_404(form.product_id.data)

    try:
        qty = Decimal(str(form.quantity.data))
    except Exception:
        flash("Некорректное количество", "danger")
        return redirect(url_for("admin.admin_sales"))

    if qty <= 0:
        flash("Количество должно быть больше 0", "danger")
        return redirect(url_for("admin.admin_sales"))

    lines = _sales_lines()
    key_prod = int(product.id)

    merged = False
    for line in lines:
        if int(line["product_id"]) == key_prod:
            line["qty"] = str(Decimal(line["qty"]) + qty)
            merged = True
            break

    if not merged:
        lines.append({
            "product_id": key_prod,
            "qty": str(qty)
        })

    _save_sales_lines(lines)
    flash(f"Добавлено в продажу: {product.name}", "success")
    return redirect(url_for("admin.admin_sales", q=request.form.get("q", "")))


@admin_bp.route("/sales/remove/<int:idx>", methods=["POST"])
@admin_required
def admin_sales_remove(idx):
    lines = _sales_lines()
    if 0 <= idx < len(lines):
        lines.pop(idx)
        _save_sales_lines(lines)
        flash("Позиция удалена из продажи", "info")
    return redirect(url_for("admin.admin_sales"))


@admin_bp.route("/sales/clear", methods=["POST"])
@admin_required
def admin_sales_clear():
    _clear_sales_lines()
    flash("Список продажи очищен", "info")
    return redirect(url_for("admin.admin_sales"))


@admin_bp.route("/sales/confirm", methods=["POST"])
@admin_required
def admin_sales_confirm():
    lines = _sales_lines()
    if not lines:
        flash("Список продажи пуст", "warning")
        return redirect(url_for("admin.admin_sales"))

    today = date.today()
    sale = Sale()
    db.session.add(sale)

    for line in lines:
        product = Product.query.get(int(line["product_id"]))
        if not product:
            continue

        need_qty = Decimal(line["qty"])
        if need_qty <= 0:
            continue

        batches = (
            Batch.query
            .filter(Batch.product_id == product.id, Batch.expires_at >= today)
            .order_by(Batch.produced_at.asc(), Batch.id.asc())
            .all()
        )

        available_qty = sum((Decimal(str(b.quantity)) for b in batches), Decimal("0"))
        if available_qty < need_qty:
            db.session.rollback()
            flash(f"Недостаточно остатков для товара '{product.name}'. Доступно: {available_qty}", "danger")
            return redirect(url_for("admin.admin_sales"))

        remains = need_qty
        source_produced_at = batches[0].produced_at if batches else None

        for batch in batches:
            if remains <= 0:
                break

            batch_qty = Decimal(str(batch.quantity))
            take_qty = batch_qty if batch_qty <= remains else remains

            remains -= take_qty
            new_qty = batch_qty - take_qty

            if new_qty <= 0:
                db.session.delete(batch)
            else:
                batch.quantity = new_qty

        unit_price = Decimal(str(product.price))
        line_total = (unit_price * need_qty).quantize(Decimal("0.01"))

        item = SaleItem(
            sale=sale,
            product_id=product.id,
            quantity=need_qty,
            unit_price=unit_price,
            line_total=line_total,
            source_produced_at=source_produced_at
        )
        db.session.add(item)

    if not sale.items:
        db.session.rollback()
        flash("Не удалось сформировать продажу", "danger")
        return redirect(url_for("admin.admin_sales"))

    db.session.commit()
    _clear_sales_lines()
    flash(f"Продажа №{sale.id} подтверждена", "success")
    return redirect(url_for("admin.admin_sales_history"))


@admin_bp.route("/sales/history", methods=["GET"])
@admin_required
def admin_sales_history():
    period = (request.args.get("period") or "").strip()
    start_date_raw = (request.args.get("start_date") or "").strip()
    end_date_raw = (request.args.get("end_date") or "").strip()
    product_id_raw = (request.args.get("product_id") or "").strip()

    filter_form = SalesHistoryFilterForm(request.args)

    product_choices = [(0, "— Все товары —")] + [
        (p.id, p.name) for p in Product.query.order_by(Product.name.asc()).all()
    ]
    filter_form.product_id.choices = product_choices

    selected_product_id = int(product_id_raw) if product_id_raw.isdigit() else 0
    filter_form.product_id.data = selected_product_id

    start_date = None
    end_date = None
    today = date.today()

    if period == "today":
        start_date = today
        end_date = today
    elif period == "yesterday":
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif period == "week":
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == "month":
        start_date = today - timedelta(days=29)
        end_date = today
    elif period == "custom":
        try:
            start_date = date.fromisoformat(start_date_raw) if start_date_raw else None
        except ValueError:
            start_date = None
        try:
            end_date = date.fromisoformat(end_date_raw) if end_date_raw else None
        except ValueError:
            end_date = None

    query = SaleItem.query.join(Sale).join(Product)

    if start_date:
        query = query.filter(db.func.date(Sale.created_at) >= start_date)
    if end_date:
        query = query.filter(db.func.date(Sale.created_at) <= end_date)

    if selected_product_id:
        query = query.filter(SaleItem.product_id == selected_product_id)

    items = query.order_by(Sale.created_at.desc(), SaleItem.id.desc()).all()

    total_sum = sum((Decimal(str(item.line_total)) for item in items), Decimal("0.00"))

    for item in items:
        qty = Decimal(str(item.quantity))
        if item.product.is_weight_based:
            item._qty_display = format(qty.normalize(), "f").rstrip("0").rstrip(".")
        else:
            item._qty_display = str(int(qty))

    return render_template(
        "admin/sales/history.html",
        items=items,
        total_sum=total_sum,
        period=period,
        start_date=start_date_raw,
        end_date=end_date_raw,
        selected_product_id=selected_product_id,
        filter_form=filter_form
    )


@admin_bp.route("/writeoffs")
@admin_required
def admin_writeoffs():
    month_ago = date.today() - timedelta(days=30)
    writeoffs = (
        WriteOff.query
        .join(Product)
        .filter(WriteOff.created_at >= month_ago)
        .order_by(WriteOff.created_at.desc())
        .all()
    )

    for row in writeoffs:
        qty = Decimal(str(row.quantity))
        if row.product.is_weight_based:
            row._qty_display = format(qty.normalize(), "f").rstrip("0").rstrip(".")
        else:
            row._qty_display = str(int(qty))

    return render_template("admin/writeoffs/index.html", writeoffs=writeoffs)
