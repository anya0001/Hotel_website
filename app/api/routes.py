from datetime import datetime, timedelta

from flask import jsonify, request
from flask_login import login_required

from app.api import api_bp
from app.models import Room


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@api_bp.route("/rooms/<int:room_id>/availability")
def check_availability(room_id):
    """
    GET /api/rooms/<id>/availability?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD
    Used by the booking form (real-time validation) before submit.
    """
    room = Room.query.get_or_404(room_id)
    check_in = _parse_date(request.args.get("check_in"))
    check_out = _parse_date(request.args.get("check_out"))

    if not check_in or not check_out or check_out <= check_in:
        return jsonify({"available": False, "error": "Invalid date range."}), 400

    available = room.is_available(check_in, check_out)
    nights = (check_out - check_in).days
    total = round(room.effective_price * nights, 2) if available else None

    return jsonify({
        "available": available,
        "nights": nights,
        "price_per_night": room.effective_price,
        "total_price": total,
    })


@api_bp.route("/rooms/<int:room_id>/calendar")
def room_calendar(room_id):
    """
    Returns per-day unit availability for the next 90 days, used to render
    the availability calendar on the room detail page.
    """
    room = Room.query.get_or_404(room_id)
    today = datetime.utcnow().date()
    days = []
    for offset in range(90):
        day = today + timedelta(days=offset)
        booked_units = room.units_booked_on(day)
        days.append({
            "date": day.isoformat(),
            "available_units": max(0, room.total_units - booked_units),
            "sold_out": booked_units >= room.total_units,
        })
    return jsonify({"room_id": room.id, "total_units": room.total_units, "days": days})


@api_bp.route("/notifications/unread-count")
@login_required
def unread_notifications_count():
    from flask_login import current_user
    from app.models import Notification

    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": count})
