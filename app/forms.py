from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileSize
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DecimalField, IntegerField, SelectField, \
    FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange
from wtforms import BooleanField

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
