from flask import render_template, request, flash, redirect, url_for, current_app, Response
from sqlalchemy import or_

from app.hotel import hotel_bp
from app.extensions import db, rate_limiter
from app.models import Room, Amenity, GalleryImage, FAQ, Promotion, Review, ContactMessage, NewsletterSubscriber
from app.forms import RoomSearchForm, ContactForm, NewsletterForm
from app.utils import allowed_file  # noqa: F401 (re-exported for templates via filters if needed)


@hotel_bp.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /auth/",
        "Disallow: /booking/",
        "Disallow: /admin/",
        "",
        f"Sitemap: {url_for('hotel.sitemap', _external=True)}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@hotel_bp.route("/sitemap.xml")
def sitemap():
    static_endpoints = ["hotel.home", "hotel.rooms", "hotel.gallery", "hotel.about", "hotel.faq", "hotel.contact"]
    urls = [url_for(ep, _external=True) for ep in static_endpoints]
    urls += [url_for("hotel.room_detail", slug=r.slug, _external=True)
             for r in Room.query.filter_by(is_active=True).all()]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@hotel_bp.route("/")
def home():
    featured_rooms = (
        Room.query.filter_by(is_active=True, is_featured=True)
        .order_by(Room.created_at.desc())
        .limit(6)
        .all()
    )
    popular_rooms = (
        Room.query.filter_by(is_active=True)
        .order_by(Room.review_count.desc(), Room.average_rating.desc())
        .limit(8)
        .all()
    )
    amenities = Amenity.query.limit(8).all()
    gallery = GalleryImage.query.filter_by(is_published=True).order_by(GalleryImage.position).limit(8).all()
    testimonials = (
        Review.query.filter_by(is_approved=True)
        .order_by(Review.rating.desc(), Review.created_at.desc())
        .limit(6)
        .all()
    )
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.position).limit(6).all()
    active_promotions = [p for p in Promotion.query.filter_by(is_active=True).all() if p.is_currently_valid]

    search_form = RoomSearchForm()
    newsletter_form = NewsletterForm()

    return render_template(
        "hotel/home.html",
        featured_rooms=featured_rooms,
        popular_rooms=popular_rooms,
        amenities=amenities,
        gallery=gallery,
        testimonials=testimonials,
        faqs=faqs,
        promotions=active_promotions,
        search_form=search_form,
        newsletter_form=newsletter_form,
    )


@hotel_bp.route("/rooms")
def rooms():
    form = RoomSearchForm(request.args, meta={"csrf": False})
    form.amenities.choices = [(a.id, a.name) for a in Amenity.query.order_by(Amenity.name).all()]

    query = Room.query.filter_by(is_active=True)

    if form.room_type.data:
        query = query.filter(Room.room_type.ilike(f"%{form.room_type.data}%"))
    if form.min_price.data is not None:
        query = query.filter(Room.price_per_night >= form.min_price.data)
    if form.max_price.data is not None:
        query = query.filter(Room.price_per_night <= form.max_price.data)
    if form.beds.data:
        query = query.filter(Room.beds >= form.beds.data)
    if form.guests.data:
        query = query.filter(Room.max_guests >= form.guests.data)
    if form.amenities.data:
        for amenity_id in form.amenities.data:
            query = query.filter(Room.amenities.any(Amenity.id == amenity_id))

    check_in, check_out = form.check_in.data, form.check_out.data
    candidate_rooms = query.all()
    if check_in and check_out and check_out > check_in:
        candidate_rooms = [r for r in candidate_rooms if r.is_available(check_in, check_out)]

    sort = form.sort.data or "recommended"
    if sort == "price_asc":
        candidate_rooms.sort(key=lambda r: r.effective_price)
    elif sort == "price_desc":
        candidate_rooms.sort(key=lambda r: r.effective_price, reverse=True)
    elif sort == "rating":
        candidate_rooms.sort(key=lambda r: (r.average_rating, r.review_count), reverse=True)
    else:
        candidate_rooms.sort(key=lambda r: (r.is_featured, r.review_count), reverse=True)

    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ROOMS_PER_PAGE"]
    total = len(candidate_rooms)
    start = (page - 1) * per_page
    page_items = candidate_rooms[start:start + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "hotel/rooms.html",
        rooms=page_items,
        form=form,
        page=page,
        total_pages=total_pages,
        total_results=total,
    )


@hotel_bp.route("/rooms/<slug>")
def room_detail(slug):
    room = Room.query.filter_by(slug=slug, is_active=True).first_or_404()
    related_rooms = (
        Room.query.filter(Room.id != room.id, Room.room_type == room.room_type, Room.is_active.is_(True))
        .limit(3)
        .all()
    )
    reviews = (
        Review.query.filter_by(room_id=room.id, is_approved=True)
        .order_by(Review.created_at.desc())
        .all()
    )
    return render_template(
        "hotel/room_detail.html",
        room=room,
        related_rooms=related_rooms,
        reviews=reviews,
    )


@hotel_bp.route("/gallery")
def gallery():
    images = GalleryImage.query.filter_by(is_published=True).order_by(GalleryImage.position).all()
    categories = sorted({img.category for img in images if img.category})
    return render_template("hotel/gallery.html", images=images, categories=categories)


@hotel_bp.route("/faq")
def faq():
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.position).all()
    categories = sorted({f.category for f in faqs if f.category})
    return render_template("hotel/faq.html", faqs=faqs, categories=categories)


@hotel_bp.route("/about")
def about():
    return render_template("hotel/about.html")


@hotel_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        if not rate_limiter.allow(f"contact:{request.remote_addr}", max_hits=5, window_seconds=3600):
            flash("Too many messages sent. Please try again later.", "warning")
            return redirect(url_for("hotel.contact"))

        msg = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            subject=form.subject.data,
            message=form.message.data.strip(),
        )
        db.session.add(msg)
        db.session.commit()
        flash("Thank you — your message has been sent. We'll reply within 24 hours.", "success")
        return redirect(url_for("hotel.contact"))
    return render_template("hotel/contact.html", form=form)


@hotel_bp.route("/newsletter", methods=["POST"])
def newsletter():
    form = NewsletterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if not NewsletterSubscriber.query.filter_by(email=email).first():
            db.session.add(NewsletterSubscriber(email=email))
            db.session.commit()
        flash("You're subscribed! Watch your inbox for exclusive offers.", "success")
    else:
        flash("Please enter a valid email address.", "danger")
    return redirect(request.referrer or url_for("hotel.home"))
