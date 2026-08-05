from flask import Blueprint

hotel_bp = Blueprint("hotel", __name__, template_folder="../templates/hotel")

from app.hotel import routes  # noqa: E402,F401
