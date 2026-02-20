import os
from uuid import uuid4
from flask import current_app

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file_storage, subdir: str) -> str:
    """
    Сохраняет файл в: <UPLOAD_FOLDER>/<subdir>/...
    Возвращает путь для БД: /static/uploads/<subdir>/xxx.webp
    """
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""

    original_filename = file_storage.filename
    if not _allowed(original_filename):
        raise ValueError("Недопустимый формат файла (jpg, jpeg, png, webp)")

    ext = original_filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid4().hex}.{ext}"

    base_folder = current_app.config["UPLOAD_FOLDER"]  # например: app/static/uploads
    folder = os.path.join(base_folder, subdir)
    os.makedirs(folder, exist_ok=True)

    abs_path = os.path.join(folder, new_name)
    file_storage.save(abs_path)

    return f"/static/uploads/{subdir}/{new_name}"

def save_product_image(file_storage) -> str:
    return save_image(file_storage, "products")

def save_category_image(file_storage) -> str:
    return save_image(file_storage, "categories")
