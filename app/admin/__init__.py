from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.app_context_processor
def inject_admin_message_count():
    from app.models import ContactMessage
    return {"unread_message_count": ContactMessage.query.filter_by(is_read=False).count()}


from app.admin import decorators  # noqa: E402,F401
from app.admin import routes  # noqa: E402,F401
