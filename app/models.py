from datetime import datetime, date
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------

class RoomAmenity(db.Model):
    __tablename__ = "room_amenities"

    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), primary_key=True)
    amenity_id = db.Column(db.Integer, db.ForeignKey("amenities.id"), primary_key=True)


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    role = db.Column(db.String(20), default=UserRole.CUSTOMER.value, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reset_token = db.Column(db.String(255))
    reset_token_expires = db.Column(db.DateTime)

    bookings = db.relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    def __repr__(self):
        return f"<User {self.email}>"


class Amenity(db.Model):
    __tablename__ = "amenities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(60), default="check")  # icon key, see static/js/icons.js

    rooms = db.relationship("Room", secondary="room_amenities", back_populates="amenities")

    def __repr__(self):
        return f"<Amenity {self.name}>"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    room_type = db.Column(db.String(60), nullable=False)  # e.g. Deluxe, Suite, Villa
    description = db.Column(db.Text, nullable=False)
    short_description = db.Column(db.String(255))

    price_per_night = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Integer, default=0)

    max_guests = db.Column(db.Integer, nullable=False, default=2)
    beds = db.Column(db.Integer, nullable=False, default=1)
    bedrooms = db.Column(db.Integer, default=1)
    size_sqm = db.Column(db.Integer)

    total_units = db.Column(db.Integer, nullable=False, default=1)  # inventory count for this room type
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    average_rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship(
        "RoomImage", back_populates="room", cascade="all, delete-orphan",
        order_by="RoomImage.position"
    )
    amenities = db.relationship("Amenity", secondary="room_amenities", back_populates="rooms")
    bookings = db.relationship("Booking", back_populates="room")
    reviews = db.relationship("Review", back_populates="room", cascade="all, delete-orphan")
    favorited_by = db.relationship("Favorite", back_populates="room", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_room_price", "price_per_night"),
        db.Index("ix_room_active_featured", "is_active", "is_featured"),
    )

    @property
    def effective_price(self):
        if self.discount_percent and self.discount_percent > 0:
            return round(float(self.price_per_night) * (1 - self.discount_percent / 100), 2)
        return float(self.price_per_night)

    @property
    def primary_image(self):
        return self.images[0] if self.images else None

    def is_available(self, check_in: date, check_out: date, exclude_booking_id=None) -> bool:
        """
        A room TYPE is available if the number of overlapping, non-cancelled
        bookings is below total_units for every night of the requested stay.
        """
        overlapping_query = Booking.query.filter(
            Booking.room_id == self.id,
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        if exclude_booking_id:
            overlapping_query = overlapping_query.filter(Booking.id != exclude_booking_id)
        overlapping_count = overlapping_query.count()
        return overlapping_count < self.total_units

    def units_booked_on(self, day: date) -> int:
        return Booking.query.filter(
            Booking.room_id == self.id,
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
            Booking.check_in <= day,
            Booking.check_out > day,
        ).count()

    def recalculate_rating(self):
        reviews = [r.rating for r in self.reviews]
        self.review_count = len(reviews)
        self.average_rating = round(sum(reviews) / len(reviews), 2) if reviews else 0.0

    def __repr__(self):
        return f"<Room {self.name}>"


class RoomImage(db.Model):
    __tablename__ = "room_images"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    thumbnail_filename = db.Column(db.String(255))
    alt_text = db.Column(db.String(255))
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    room = db.relationship("Room", back_populates="images")


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)

    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False, default=1)

    nights = db.Column(db.Integer, nullable=False)
    price_per_night = db.Column(db.Numeric(10, 2), nullable=False)  # snapshot at booking time
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(db.String(20), default=BookingStatus.PENDING.value, nullable=False)
    special_requests = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="bookings")
    room = db.relationship("Room", back_populates="bookings")

    __table_args__ = (
        db.Index("ix_booking_dates", "room_id", "check_in", "check_out"),
        db.CheckConstraint("check_out > check_in", name="ck_booking_dates_order"),
    )

    @property
    def is_upcoming(self):
        return self.check_in >= date.today() and self.status in (
            BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value
        )

    @property
    def is_past(self):
        return self.check_out < date.today() or self.status == BookingStatus.COMPLETED.value

    def __repr__(self):
        return f"<Booking {self.reference}>"


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"))

    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(150))
    body = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="reviews")
    room = db.relationship("Room", back_populates="reviews")

    __table_args__ = (
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="favorites")
    room = db.relationship("Room", back_populates="favorited_by")

    __table_args__ = (db.UniqueConstraint("user_id", "room_id", name="uq_favorite_user_room"),)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.String(500))
    url = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="notifications")


class FAQ(db.Model):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), default="General")
    position = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    thumbnail_filename = db.Column(db.String(255))
    caption = db.Column(db.String(255))
    category = db.Column(db.String(60), default="Hotel")
    position = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Promotion(db.Model):
    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.String(30), unique=True)
    discount_percent = db.Column(db.Integer, nullable=False, default=10)
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    image_filename = db.Column(db.String(255))

    @property
    def is_currently_valid(self):
        today = date.today()
        if not self.is_active:
            return False
        if self.starts_on and today < self.starts_on:
            return False
        if self.ends_on and today > self.ends_on:
            return False
        return True


class SiteSetting(db.Model):
    """
    Generic key/value store that powers 'Manage Homepage' style admin
    screens (hero headline, stats, testimonials JSON, etc.) without a
    dedicated table + migration for every tiny piece of copy.
    """
    __tablename__ = "site_settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)
    value_type = db.Column(db.String(20), default="text")  # text | json | number | bool

    @staticmethod
    def get(key, default=None):
        row = db.session.get(SiteSetting, key)
        if not row:
            return default
        if row.value_type == "json":
            import json
            try:
                return json.loads(row.value)
            except (TypeError, ValueError):
                return default
        if row.value_type == "number":
            try:
                return float(row.value)
            except (TypeError, ValueError):
                return default
        if row.value_type == "bool":
            return str(row.value).lower() in ("1", "true", "yes")
        return row.value if row.value is not None else default

    @staticmethod
    def set(key, value, value_type="text"):
        import json
        row = db.session.get(SiteSetting, key)
        if not row:
            row = SiteSetting(key=key)
            db.session.add(row)
        row.value = json.dumps(value) if value_type == "json" else str(value)
        row.value_type = value_type
        db.session.commit()
        return row


class ContactMessage(db.Model):
    """Stores submissions from the public contact form."""
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
