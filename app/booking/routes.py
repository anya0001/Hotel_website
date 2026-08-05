from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.booking import booking_bp
from app.extensions import db
from app.models import Room, Booking, BookingStatus, Favorite, Review, Notification
from app.forms import BookingForm, ReviewForm, DeleteForm
from app.utils import generate_booking_reference
from app.email import send_booking_confirmation_email


@booking_bp.route("/new/<slug>", methods=["GET", "POST"])
@login_required
def new_booking(slug):
    room = Room.query.filter_by(slug=slug, is_active=True).first_or_404()
    form = BookingForm()

    if request.method == "GET":
        form.check_in.data = request.args.get("check_in") and datetime.strptime(
            request.args["check_in"], "%Y-%m-%d"
        ).date()
        form.check_out.data = request.args.get("check_out") and datetime.strptime(
            request.args["check_out"], "%Y-%m-%d"
        ).date()
        form.guests.data = request.args.get("guests", type=int) or min(2, room.max_guests)

    if form.validate_on_submit():
        if form.guests.data > room.max_guests:
            flash(f"This room sleeps a maximum of {room.max_guests} guests.", "danger")
            return render_template("booking/new.html", room=room, form=form)

        if not room.is_available(form.check_in.data, form.check_out.data):
            flash("Sorry — this room is no longer available for those dates.", "danger")
            return render_template("booking/new.html", room=room, form=form)

        nights = (form.check_out.data - form.check_in.data).days
        total_price = round(room.effective_price * nights, 2)

        booking = Booking(
            reference=generate_booking_reference(),
            user_id=current_user.id,
            room_id=room.id,
            check_in=form.check_in.data,
            check_out=form.check_out.data,
            guests=form.guests.data,
            nights=nights,
            price_per_night=room.effective_price,
            total_price=total_price,
            status=BookingStatus.CONFIRMED.value,
            special_requests=form.special_requests.data,
        )
        db.session.add(booking)

        db.session.add(Notification(
            user_id=current_user.id,
            title="Booking confirmed",
            body=f"Your stay at {room.name} ({booking.reference}) is confirmed.",
            url=url_for("booking.confirmation", reference=booking.reference),
        ))
        db.session.commit()

        send_booking_confirmation_email(booking)

        flash("Your booking is confirmed! A confirmation email is on its way.", "success")
        return redirect(url_for("booking.confirmation", reference=booking.reference))

    return render_template("booking/new.html", room=room, form=form)


@booking_bp.route("/confirmation/<reference>")
@login_required
def confirmation(reference):
    booking = Booking.query.filter_by(reference=reference).first_or_404()
    if booking.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template("booking/confirmation.html", booking=booking)


@booking_bp.route("/history")
@login_required
def history():
    tab = request.args.get("tab", "upcoming")
    base_query = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.check_in.desc())

    if tab == "past":
        bookings = [b for b in base_query.all() if b.is_past and b.status != BookingStatus.CANCELLED.value]
    elif tab == "cancelled":
        bookings = base_query.filter_by(status=BookingStatus.CANCELLED.value).all()
    else:
        tab = "upcoming"
        bookings = [b for b in base_query.all() if b.is_upcoming]

    delete_form = DeleteForm()
    return render_template("booking/history.html", bookings=bookings, tab=tab, delete_form=delete_form)


@booking_bp.route("/<reference>/cancel", methods=["POST"])
@login_required
def cancel(reference):
    form = DeleteForm()
    booking = Booking.query.filter_by(reference=reference).first_or_404()
    if booking.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    if not form.validate_on_submit():
        flash("Could not process request. Please try again.", "danger")
        return redirect(url_for("booking.history"))

    if booking.status == BookingStatus.CANCELLED.value:
        flash("This booking is already cancelled.", "info")
    elif booking.check_in <= datetime.utcnow().date():
        flash("This booking can no longer be cancelled online — please contact us.", "warning")
    else:
        booking.status = BookingStatus.CANCELLED.value
        booking.cancelled_at = datetime.utcnow()
        db.session.commit()
        flash(f"Booking {booking.reference} has been cancelled.", "success")

    return redirect(url_for("booking.history"))


# ---------------------------------------------------------------------------
# Favorites ("saved rooms")
# ---------------------------------------------------------------------------

@booking_bp.route("/favorites")
@login_required
def favorites():
    saved = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return render_template("booking/favorites.html", favorites=saved)


@booking_bp.route("/favorites/<int:room_id>/toggle", methods=["POST"])
@login_required
def toggle_favorite(room_id):
    room = Room.query.get_or_404(room_id)
    existing = Favorite.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from saved rooms.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, room_id=room.id))
        db.session.commit()
        flash("Saved to your favorites.", "success")
    return redirect(request.referrer or url_for("hotel.room_detail", slug=room.slug))


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@booking_bp.route("/rooms/<slug>/review", methods=["GET", "POST"])
@login_required
def add_review(slug):
    room = Room.query.filter_by(slug=slug).first_or_404()

    completed_booking = Booking.query.filter_by(
        user_id=current_user.id, room_id=room.id
    ).filter(Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value])).first()

    if not completed_booking:
        flash("You can only review rooms you've booked.", "warning")
        return redirect(url_for("hotel.room_detail", slug=slug))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            user_id=current_user.id,
            room_id=room.id,
            booking_id=completed_booking.id,
            rating=int(form.rating.data),
            title=form.title.data,
            body=form.body.data.strip(),
        )
        db.session.add(review)
        db.session.flush()
        room.recalculate_rating()
        db.session.commit()
        flash("Thank you for your review!", "success")
        return redirect(url_for("hotel.room_detail", slug=slug))

    return render_template("booking/add_review.html", room=room, form=form)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@booking_bp.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    unread = [n for n in items if not n.is_read]
    for n in unread:
        n.is_read = True
    if unread:
        db.session.commit()
    return render_template("booking/notifications.html", notifications=items)
