from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileSize
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    DecimalField, IntegerField, SelectField, FileField, BooleanField, DateField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class ProductForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    description = TextAreaField("Описание", validators=[Optional()])
    details = TextAreaField("Детали (пищевая/тех. инфа)", validators=[Optional()])

    is_weight_based = BooleanField("Весовой товар")
    price = DecimalField("Цена", places=2, validators=[DataRequired(), NumberRange(min=0)])

    min_weight = IntegerField("Мин. вес (г)", validators=[Optional(), NumberRange(min=0)])
    max_weight = IntegerField("Макс. вес (г)", validators=[Optional(), NumberRange(min=0)])

    is_frozen = BooleanField("Замороженный")
    is_discounted = BooleanField("Скидка")

    supplier_name = StringField("Поставщик", validators=[Optional()])
    tags = StringField("Теги", validators=[Optional()])

    category_id = SelectField("Категория", coerce=int, validators=[Optional()])

    # ✅ новое поле под твою модель
    shelf_life_days = IntegerField(
        "Срок годности (дней)",
        validators=[DataRequired(), NumberRange(min=1, max=365)]
    )

    image = FileField("Фото товара", validators=[
        Optional(),
        FileAllowed(["jpg", "jpeg", "png", "webp"], "Только jpg/jpeg/png/webp")
    ])

    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired(), Length(max=128)])

    image = FileField(
        "Фото категории",
        validators=[
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Только картинки"),
            FileSize(max_size=5 * 1024 * 1024, message="Макс 5MB")
        ]
    )

    submit = SubmitField("Сохранить")


# -------------------------
# ✅ Поставка / Склад
# -------------------------

class SupplySearchForm(FlaskForm):
    q = StringField("Поиск товара", validators=[Optional(), Length(max=120)])
    submit = SubmitField("Найти")


class SupplyAddLineForm(FlaskForm):
    product_id = IntegerField(validators=[DataRequired()])

    quantity = DecimalField(
        "Количество",
        places=3,
        validators=[DataRequired(), NumberRange(min=0.001)]
    )

    produced_at = DateField(
        "Дата изготовления",
        validators=[Optional()],
        default=date.today
    )

    submit = SubmitField("Добавить в поставку")

class SalesAddLineForm(FlaskForm):
    product_id = IntegerField(validators=[DataRequired()])

    quantity = DecimalField(
        "Количество",
        places=3,
        validators=[DataRequired(), NumberRange(min=0.001)]
    )

    submit = SubmitField("Добавить в продажу")


class SalesHistoryFilterForm(FlaskForm):
    period = SelectField(
        "Период",
        choices=[
            ("", "— За всё время —"),
            ("today", "За сегодня"),
            ("yesterday", "За вчера"),
            ("week", "За последнюю неделю"),
            ("month", "За последний месяц"),
            ("custom", "Свой интервал")
        ],
        validators=[Optional()]
    )

    start_date = DateField("Дата с", validators=[Optional()])
    end_date = DateField("Дата по", validators=[Optional()])
    product_id = SelectField("Товар", coerce=int, validators=[Optional()])

    submit = SubmitField("Применить")
