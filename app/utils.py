import os
import uuid
import secrets
import string

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename


def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_image(file_storage, subfolder="rooms"):
    """
    Saves an uploaded image (resized + a thumbnail) to
    static/images/uploads/<subfolder>/ and returns (filename, thumbnail_filename)
    as paths relative to that folder, or (None, None) if no file was given.

    Images are compressed and capped at IMAGE_MAX_DIMENSION on the long edge,
    which keeps the site fast without a CDN/image-processing service.
    """
    if not file_storage or not file_storage.filename:
        return None, None

    if not allowed_file(file_storage.filename):
        raise ValueError("Unsupported file type. Use JPG, PNG, or WEBP.")

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    base_name = secure_filename(uuid.uuid4().hex)
    filename = f"{base_name}.{ext}"
    thumb_filename = f"{base_name}_thumb.{ext}"

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    full_path = os.path.join(upload_dir, filename)
    thumb_path = os.path.join(upload_dir, thumb_filename)

    image = Image.open(file_storage.stream)
    image = image.convert("RGB") if image.mode in ("P", "RGBA") and ext in ("jpg", "jpeg") else image

    max_dim = current_app.config["IMAGE_MAX_DIMENSION"]
    image_copy = image.copy()
    image_copy.thumbnail((max_dim, max_dim), Image.LANCZOS)
    save_kwargs = {"quality": 85, "optimize": True} if ext in ("jpg", "jpeg") else {"optimize": True}
    image_copy.save(full_path, **save_kwargs)

    thumb = image.copy()
    thumb.thumbnail(current_app.config["THUMBNAIL_SIZE"], Image.LANCZOS)
    thumb.save(thumb_path, **save_kwargs)

    return f"{subfolder}/{filename}", f"{subfolder}/{thumb_filename}"


def delete_image(relative_path):
    if not relative_path:
        return
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            current_app.logger.warning("Could not delete file: %s", full_path)


def generate_booking_reference() -> str:
    """Generates a human-friendly, collision-resistant booking reference, e.g. LX-8F3K92."""
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"LX-{suffix}"


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")
