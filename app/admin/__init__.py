from flask import Blueprint, g

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_request
def capture_message_read_state():
    if g.get("message_read_state_captured"):
        return

    if getattr(g, "current_user", None) is None:
        return

    # The messages list should not mark messages as read just because the inbox was opened.
    # Preserve the unread state for the current request so the existing list route can render
    # normally, then restore those records after the response is rendered.
    if getattr(__import__("flask").request, "endpoint", "") == "admin.messages_list":
        from app.models import ContactMessage
        unread_messages = ContactMessage.query.filter_by(is_read=False).all()
        g.message_unread_ids = {message.id for message in unread_messages}
        g.message_unread_count = len(unread_messages)
        g.message_read_state_captured = True


@admin_bp.after_request
def restore_message_read_state(response):
    unread_ids = g.get("message_unread_ids")
    if unread_ids is not None:
        from app.models import ContactMessage
        messages = ContactMessage.query.filter(ContactMessage.id.in_(unread_ids)).all()
        for message in messages:
            message.is_read = False
        from app.extensions import db
        db.session.commit()
    return response


@admin_bp.app_context_processor
def inject_admin_message_count():
    from app.models import ContactMessage
    unread_count = g.get("message_unread_count")
    if unread_count is None:
        unread_count = ContactMessage.query.filter_by(is_read=False).count()
    return {"unread_message_count": unread_count, "unread_message_ids": g.get("message_unread_ids", set())}


from app.admin import decorators  # noqa: E402,F401
from app.admin import message_status  # noqa: E402,F401
from app.admin import routes  # noqa: E402,F401
