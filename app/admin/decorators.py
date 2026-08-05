from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view_func):
    """Combines login_required with an admin-role check (403 for non-admins)."""
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped
