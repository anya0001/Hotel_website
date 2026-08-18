from flask import redirect, url_for, flash

from app.admin import admin_bp
from app.admin.decorators import admin_required
from app.extensions import db
from app.forms import DeleteForm
from app.models import ContactMessage


@admin_bp.route("/messages/<int:message_id>/toggle-read", methods=["POST"])
@admin_required
def message_toggle_read(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    form = DeleteForm()

    if form.validate_on_submit():
        message.is_read = not message.is_read
        db.session.commit()
        flash("Message marked as read." if message.is_read else "Message marked as unread.", "success")

    return redirect(url_for("admin.messages_list", q=""))
