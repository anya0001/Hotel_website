from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, current_app
from sqlalchemy import func, or_

from app.admin import admin_bp
from app.admin.decorators import admin_required
from app.extensions import db
from app.models import (
    Room, RoomImage, Amenity, Booking, BookingStatus, User, Review,
    GalleryImage, FAQ, Promotion, SiteSetting, ContactMessage
)
from app.forms import (
    RoomForm, AmenityForm, FAQForm, GalleryImageForm, PromotionForm,
    UserAdminForm, HomepageSettingsForm, BookingStatusForm, DeleteForm
)
from app.utils import save_image, delete_image, slugify


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@admin_required
def dashboard():
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    total_revenue = db.session.query(func.coalesce(func.sum(Booking.total_price), 0)).filter(
        Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value])
    ).scalar()

    month_revenue = db.session.query(func.coalesce(func.sum(Booking.total_price), 0)).filter(
        Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value]),
        Booking.created_at >= month_start,
    ).scalar()

    stats = {
        "total_revenue": float(total_revenue or 0),
        "month_revenue": float(month_revenue or 0),
        "total_bookings": Booking.query.count(),
        "upcoming_bookings": Booking.query.filter(
            Booking.check_in >= today,
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value])
        ).count(),
        "total_users": User.query.filter_by(role="customer").count(),
        "total_rooms": Room.query.count(),
        "active_rooms": Room.query.filter_by(is_active=True).count(),
        "pending_reviews": Review.query.filter_by(is_approved=False).count(),
        "unread_messages": ContactMessage.query.filter_by(is_read=False).count(),
    }

    # Last 6 months revenue for the chart
    monthly_labels, monthly_revenue = [], []
    months = []
    cursor = month_start
    for _ in range(6):
        months.append(cursor)
        prev_month = cursor.month - 1 or 12
        prev_year = cursor.year - 1 if cursor.month == 1 else cursor.year
        cursor = cursor.replace(year=prev_year, month=prev_month, day=1)
    months.reverse()

    for i, m_start in enumerate(months):
        if i + 1 < len(months):
            m_end = months[i + 1]
        else:
            next_month = m_start.month % 12 + 1
            next_year = m_start.year + 1 if m_start.month == 12 else m_start.year
            m_end = m_start.replace(year=next_year, month=next_month, day=1)
        revenue = db.session.query(func.coalesce(func.sum(Booking.total_price), 0)).filter(
            Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value]),
            Booking.created_at >= m_start,
            Booking.created_at < m_end,
        ).scalar()
        monthly_labels.append(m_start.strftime("%b"))
        monthly_revenue.append(float(revenue or 0))

    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
    top_rooms = Room.query.order_by(Room.review_count.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        monthly_labels=monthly_labels,
        monthly_revenue=monthly_revenue,
        recent_bookings=recent_bookings,
        top_rooms=top_rooms,
    )


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@admin_bp.route("/rooms")
@admin_required
def rooms_list():
    page = request.args.get("page", 1, type=int)
    pagination = Room.query.order_by(Room.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False
    )
    delete_form = DeleteForm()
    return render_template("admin/rooms_list.html", pagination=pagination, delete_form=delete_form)


@admin_bp.route("/rooms/new", methods=["GET", "POST"])
@admin_required
def room_new():
    form = RoomForm()
    form.amenities.choices = [(a.id, a.name) for a in Amenity.query.order_by(Amenity.name).all()]

    if form.validate_on_submit():
        slug_base = slugify(form.name.data)
        slug = slug_base
        counter = 1
        while Room.query.filter_by(slug=slug).first():
            counter += 1
            slug = f"{slug_base}-{counter}"

        room = Room(slug=slug)
        _apply_room_form(room, form)
        db.session.add(room)
        db.session.commit()
        _save_room_images(room, request.files.getlist("images"))
        db.session.commit()
        flash(f'Room "{room.name}" created.', "success")
        return redirect(url_for("admin.rooms_list"))

    return render_template("admin/room_form.html", form=form, room=None)


@admin_bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@admin_required
def room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    form.amenities.choices = [(a.id, a.name) for a in Amenity.query.order_by(Amenity.name).all()]

    if request.method == "GET":
        form.amenities.data = [a.id for a in room.amenities]

    if form.validate_on_submit():
        _apply_room_form(room, form)
        db.session.commit()
        _save_room_images(room, request.files.getlist("images"))
        db.session.commit()
        flash(f'Room "{room.name}" updated.', "success")
        return redirect(url_for("admin.rooms_list"))

    return render_template("admin/room_form.html", form=form, room=room)


@admin_bp.route("/rooms/<int:room_id>/delete", methods=["POST"])
@admin_required
def room_delete(room_id):
    form = DeleteForm()
    room = Room.query.get_or_404(room_id)
    if form.validate_on_submit():
        for image in room.images:
            delete_image(image.filename)
            delete_image(image.thumbnail_filename)
        db.session.delete(room)
        db.session.commit()
        flash(f'Room "{room.name}" deleted.', "info")
    return redirect(url_for("admin.rooms_list"))


@admin_bp.route("/rooms/images/<int:image_id>/delete", methods=["POST"])
@admin_required
def room_image_delete(image_id):
    form = DeleteForm()
    image = RoomImage.query.get_or_404(image_id)
    room_id = image.room_id
    if form.validate_on_submit():
        delete_image(image.filename)
        delete_image(image.thumbnail_filename)
        db.session.delete(image)
        db.session.commit()
        flash("Image removed.", "info")
    return redirect(url_for("admin.room_edit", room_id=room_id))


def _apply_room_form(room, form):
    room.name = form.name.data.strip()
    room.room_type = form.room_type.data
    room.short_description = form.short_description.data
    room.description = form.description.data
    room.price_per_night = form.price_per_night.data
    room.discount_percent = form.discount_percent.data or 0
    room.max_guests = form.max_guests.data
    room.beds = form.beds.data
    room.bedrooms = form.bedrooms.data or 1
    room.size_sqm = form.size_sqm.data
    room.total_units = form.total_units.data
    room.is_featured = form.is_featured.data
    room.is_active = form.is_active.data
    room.amenities = Amenity.query.filter(Amenity.id.in_(form.amenities.data or [])).all()


def _save_room_images(room, file_list):
    position = len(room.images)
    for file_storage in file_list:
        if not file_storage or not file_storage.filename:
            continue
        try:
            filename, thumb = save_image(file_storage, subfolder="rooms")
        except ValueError as exc:
            flash(str(exc), "danger")
            continue
        if filename:
            db.session.add(RoomImage(
                room_id=room.id, filename=filename, thumbnail_filename=thumb,
                alt_text=room.name, position=position
            ))
            position += 1


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@admin_bp.route("/bookings")
@admin_required
def bookings_list():
    status_filter = request.args.get("status", "")
    search = request.args.get("q", "").strip()

    query = Booking.query.join(Booking.user).join(Booking.room)
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            Booking.reference.ilike(search_term),
            User.full_name.ilike(search_term),
            User.email.ilike(search_term),
            Room.name.ilike(search_term),
        ))

    query = query.order_by(Booking.check_in.desc())
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False)
    status_form = BookingStatusForm()
    return render_template(
        "admin/bookings_list.html",
        pagination=pagination,
        status_filter=status_filter,
        search=search,
        status_form=status_form,
    )


@admin_bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
@admin_required
def booking_update_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    form = BookingStatusForm()
    if form.validate_on_submit():
        booking.status = form.status.data
        if form.status.data == BookingStatus.CANCELLED.value:
            booking.cancelled_at = datetime.utcnow()
        db.session.commit()
        flash(f"Booking {booking.reference} marked as {form.status.data}.", "success")
    return redirect(url_for("admin.bookings_list", q=request.args.get("q", ""), status=request.args.get("status", "")))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@admin_bp.route("/users")
@admin_required
def users_list():