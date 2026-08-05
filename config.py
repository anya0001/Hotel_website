"""
Application configuration.

Config is selected via the FLASK_ENV / FLASK_CONFIG environment variable.
DevelopmentConfig -> SQLite (zero-setup local dev)
ProductionConfig  -> PostgreSQL (Render / any Postgres host)
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Flask-WTF / CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # File uploads
    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "images", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    IMAGE_MAX_DIMENSION = 1920
    THUMBNAIL_SIZE = (480, 320)

    # Pagination
    ROOMS_PER_PAGE = 9
    BOOKINGS_PER_PAGE = 10
    REVIEWS_PER_PAGE = 6
    ADMIN_ROWS_PER_PAGE = 15

    # Mail (used for booking confirmations / password reset)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@luxstay-hotel.com")
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "1") == "1"

    HOTEL_NAME = "LuxStay Hotel & Resort"
    HOTEL_PHONE = "+1 (555) 019-2842"
    HOTEL_EMAIL = "reservations@luxstay-hotel.com"
    HOTEL_ADDRESS = "18 Marina Boulevard, Coral Bay"
    HOTEL_LAT = 25.0805
    HOTEL_LNG = 55.1403

    # Simple in-memory rate limiting defaults (see app/extensions.py)
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_LOGIN = "10 per minute"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "hotel_dev.sqlite")
    )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "").replace(
        "postgres://", "postgresql://", 1
    ) or os.environ.get("DEV_DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "hotel.sqlite"))

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
