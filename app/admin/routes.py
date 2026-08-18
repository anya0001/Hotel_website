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
    search = request.args.get("q", "").strip()
    query = Room.query
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            Room.name.ilike(search_term),
            Room.room_type.ilike(search_term),
        ))
    pagination = query.order_by(Room.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False
    )
    delete_form = DeleteForm()
    return render_template("admin/rooms_list.html", pagination=pagination, delete_form=delete_form, search=search)


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
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    query = User.query
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            User.full_name.ilike(search_term),
            User.email.ilike(search_term),
            User.role.ilike(search_term),
        ))
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False
    )
    delete_form = DeleteForm()
    return render_template("admin/users_list.html", pagination=pagination, delete_form=delete_form, search=search)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserAdminForm(obj=user)
    if form.validate_on_submit():
        if User.query.filter(User.email == form.email.data.lower(), User.id != user.id).first():
            flash("Another account already uses that email.", "danger")
        else:
            user.full_name = form.full_name.data.strip()
            user.email = form.email.data.strip().lower()
            user.phone = form.phone.data
            user.role = form.role.data
            user.is_active = form.is_active.data
            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("admin.users_list"))

    return render_template("admin/user_form.html", form=form, user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    form = DeleteForm()
    user = User.query.get_or_404(user_id)
    if form.validate_on_submit():
        if user.is_admin and User.query.filter_by(role="admin").count() <= 1:
            flash("You can't delete the last remaining administrator.", "danger")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("User deleted.", "info")
    return redirect(url_for("admin.users_list"))


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@admin_bp.route("/reviews")
@admin_required
def reviews_list():
    page = request.args.get("page", 1, type=int)
    pagination = Review.query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False
    )
    delete_form = DeleteForm()
    return render_template("admin/reviews_list.html", pagination=pagination, delete_form=delete_form)


@admin_bp.route("/reviews/<int:review_id>/toggle-approval", methods=["POST"])
@admin_required
def review_toggle_approval(review_id):
    form = DeleteForm()
    review = Review.query.get_or_404(review_id)
    if form.validate_on_submit():
        review.is_approved = not review.is_approved
        review.room.recalculate_rating()
        db.session.commit()
        flash("Review updated.", "success")
    return redirect(url_for("admin.reviews_list"))


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@admin_required
def review_delete(review_id):
    form = DeleteForm()
    review = Review.query.get_or_404(review_id)
    if form.validate_on_submit():
        room = review.room
        db.session.delete(review)
        db.session.flush()
        room.recalculate_rating()
        db.session.commit()
        flash("Review deleted.", "info")
    return redirect(url_for("admin.reviews_list"))


# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------

@admin_bp.route("/amenities", methods=["GET", "POST"])
@admin_required
def amenities_list():
    form = AmenityForm()
    if form.validate_on_submit():
        db.session.add(Amenity(name=form.name.data.strip(), icon=form.icon.data))
        db.session.commit()
        flash("Amenity added.", "success")
        return redirect(url_for("admin.amenities_list"))

    amenities = Amenity.query.order_by(Amenity.name).all()
    delete_form = DeleteForm()
    return render_template("admin/amenities_list.html", amenities=amenities, form=form, delete_form=delete_form)


@admin_bp.route("/amenities/<int:amenity_id>/delete", methods=["POST"])
@admin_required
def amenity_delete(amenity_id):
    form = DeleteForm()
    amenity = Amenity.query.get_or_404(amenity_id)
    if form.validate_on_submit():
        db.session.delete(amenity)
        db.session.commit()
        flash("Amenity removed.", "info")
    return redirect(url_for("admin.amenities_list"))


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------

@admin_bp.route("/gallery", methods=["GET", "POST"])
@admin_required
def gallery_list():
    form = GalleryImageForm()
    if form.validate_on_submit():
        try:
            filename, thumb = save_image(form.image.data, subfolder="gallery")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.gallery_list"))

        if not filename:
            flash("Please choose an image to upload.", "danger")
            return redirect(url_for("admin.gallery_list"))

        db.session.add(GalleryImage(
            filename=filename, thumbnail_filename=thumb, alt_text=form.caption.data,
            category=form.category.data, position=form.position.data or 0,
            is_published=form.is_published.data,
        ))
        db.session.commit()
        flash("Image added to gallery.", "success")
        return redirect(url_for("admin.gallery_list"))

    images = GalleryImage.query.order_by(GalleryImage.position).all()
    delete_form = DeleteForm()
    return render_template("admin/gallery_list.html", images=images, form=form, delete_form=delete_form)


@admin_bp.route("/gallery/<int:image_id>/delete", methods=["POST"])
@admin_required
def gallery_delete(image_id):
    delete_form = DeleteForm()
    image = GalleryImage.query.get_or_404(image_id)
    if delete_form.validate_on_submit():
        delete_image(image.filename)
        delete_image(image.thumbnail_filename)
        db.session.delete(image)
        db.session.commit()
        flash("Image deleted.", "info")
    return redirect(url_for("admin.gallery_list"))


# ---------------------------------------------------------------------------
# Promotions
# ---------------------------------------------------------------------------

@admin_bp.route("/promotions", methods=["GET", "POST"])
@admin_required
def promotions_list():
    form = PromotionForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            try:
                image_filename, _ = save_image(form.image.data, subfolder="promotions")
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("admin.promotions_list"))

        db.session.add(Promotion(
            title=form.title.data.strip(),
            description=form.description.data,
            code=form.code.data.upper().strip() if form.code.data else None,
            discount_percent=form.discount_percent.data,
            starts_on=form.starts_on.data,
            ends_on=form.ends_on.data,
            is_active=form.is_active.data,
            image_filename=image_filename,
        ))
        db.session.commit()
        flash("Promotion created.", "success")
        return redirect(url_for("admin.promotions_list"))

    promotions = Promotion.query.order_by(Promotion.id.desc()).all()
    delete_form = DeleteForm()
    return render_template("admin/promotions_list.html", promotions=promotions, form=form, delete_form=delete_form)


@admin_bp.route("/promotions/<int:promo_id>/delete", methods=["POST"])
@admin_required
def promotion_delete(promo_id):
    form = DeleteForm()
    promo = Promotion.query.get_or_404(promo_id)
    if form.validate_on_submit():
        delete_image(promo.image_filename)
        db.session.delete(promo)
        db.session.commit()
        flash("Promotion deleted.", "info")
    return redirect(url_for("admin.promotions_list"))


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

@admin_bp.route("/faq", methods=["GET", "POST"])
@admin_required
def faq_list():
    form = FAQForm()
    if form.validate_on_submit():
        db.session.add(FAQ(
            question=form.question.data.strip(),
            answer=form.answer.data.strip(),
            category=form.category.data or "General",
            position=form.position.data or 0,
            is_published=form.is_published.data,
        ))
        db.session.commit()
        flash("FAQ added.", "success")
        return redirect(url_for("admin.faq_list"))

    faqs = FAQ.query.order_by(FAQ.position).all()
    delete_form = DeleteForm()
    return render_template("admin/faq_list.html", faqs=faqs, form=form, delete_form=delete_form)


@admin_bp.route("/faq/<int:faq_id>/delete", methods=["POST"])
@admin_required
def faq_delete(faq_id):
    form = DeleteForm()
    faq_item = FAQ.query.get_or_404(faq_id)
    if form.validate_on_submit():
        db.session.delete(faq_item)
        db.session.commit()
        flash("FAQ removed.", "info")
    return redirect(url_for("admin.faq_list"))


# ---------------------------------------------------------------------------
# Homepage content settings
# ---------------------------------------------------------------------------

@admin_bp.route("/homepage", methods=["GET", "POST"])
@admin_required
def homepage_settings():
    form = HomepageSettingsForm()
    keys = [
        "hero_title", "hero_subtitle",
        "stat_1_value", "stat_1_label", "stat_2_value", "stat_2_label",
        "stat_3_value", "stat_3_label", "stat_4_value", "stat_4_label",
    ]

    if form.validate_on_submit():
        for key in keys:
            SiteSetting.set(key, getattr(form, key).data)
        flash("Homepage content updated.", "success")
        return redirect(url_for("admin.homepage_settings"))

    if request.method == "GET":
        defaults = {
            "hero_title": "An Unforgettable Stay Awaits",
            "hero_subtitle": "Luxury rooms, oceanfront views, and service beyond compare.",
            "stat_1_value": "200+", "stat_1_label": "Rooms & Suites",
            "stat_2_value": "15k+", "stat_2_label": "Happy Guests",
            "stat_3_value": "4.9", "stat_3_label": "Average Rating",
            "stat_4_value": "12", "stat_4_label": "Years of Excellence",
        }
        for key in keys:
            getattr(form, key).data = SiteSetting.get(key, defaults.get(key))

    return render_template("admin/homepage_settings.html", form=form)


# ---------------------------------------------------------------------------
# Contact messages
# ---------------------------------------------------------------------------

@admin_bp.route("/messages")
@admin_required
def messages_list():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    query = ContactMessage.query
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            ContactMessage.name.ilike(search_term),
            ContactMessage.email.ilike(search_term),
            ContactMessage.subject.ilike(search_term),
            ContactMessage.message.ilike(search_term),
        ))
    pagination = query.order_by(ContactMessage.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ADMIN_ROWS_PER_PAGE"], error_out=False
    )
    for m in pagination.items:
        m.is_read = True
    db.session.commit()
    return render_template("admin/messages_list.html", pagination=pagination, search=search)
