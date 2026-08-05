"""
Centralized extension instances.

Kept separate from __init__.py so blueprints/models can import
`db`, `login_manager`, etc. without circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_mail import Mail
from collections import defaultdict
from time import time

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


class SimpleRateLimiter:
    """
    Lightweight in-memory rate limiter (per-process).

    Good enough for a single-dyno deployment and keeps the project
    dependency-free. Swap for Flask-Limiter + Redis behind a load
    balancer / multi-worker Gunicorn setup.
    """

    def __init__(self):
        self._hits = defaultdict(list)

    def allow(self, key: str, max_hits: int, window_seconds: int) -> bool:
        now = time()
        window_start = now - window_seconds
        hits = [t for t in self._hits[key] if t > window_start]
        hits.append(now)
        self._hits[key] = hits
        return len(hits) <= max_hits


rate_limiter = SimpleRateLimiter()
