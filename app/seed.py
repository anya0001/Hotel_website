"""
Populates the database with realistic demo content so the site looks
production-ready out of the box. Run with: flask seed-db

Uses solid-color placeholder JPGs (generated on the fly with Pillow) for
room/gallery images so the project has zero external asset dependencies.
"""
import os
import random
from datetime import date, timedelta

from PIL import Image, ImageDraw

from app.extensions import db
from app.models import (
    User, Room, RoomImage, Amenity, Booking, BookingStatus, Review,
    FAQ, GalleryImage, Promotion, SiteSetting
)
from app.utils import slugify, generate_booking_reference
from flask import current_app

ROOM_DATA = [
    dict(name="Ocean Breeze Deluxe", room_type="Deluxe", price=189, guests=2, beds=1, bedrooms=1,
         size=32, units=8, featured=True,
         short="Bright deluxe room with a private balcony overlooking the bay.",
         desc="Wake up to uninterrupted ocean views in this Ocean Breeze Deluxe room. "
              "Featuring a plush king bed, a marble en-suite bathroom, and a private "
              "balcony perfect for sunrise coffee, this room blends resort comfort with "
              "understated elegance. Floor-to-ceiling windows fill the space with natural "
              "light throughout the day."),
    dict(name="Garden View Suite", room_type="Suite", price=259, guests=3, beds=2, bedrooms=1,
         size=45, units=6, featured=True,
         short="Spacious suite overlooking our tropical gardens, with a separate lounge.",
         desc="The Garden View Suite offers a generous separate living area alongside the "
              "bedroom, ideal for families or extended stays. Sliding doors open onto a "
              "furnished terrace facing the resort's tropical gardens. Includes a Nespresso "
              "bar, walk-in wardrobe, and a rain shower."),
    dict(name="Presidential Ocean Villa", room_type="Villa", price=650, guests=6, beds=3, bedrooms=3,
         size=120, units=2, featured=True,
         short="Three-bedroom private villa with a plunge pool and butler service.",
         desc="Our most exclusive accommodation: a three-bedroom villa with a private "
              "infinity-edge plunge pool, dedicated butler service, and direct beach "
              "access. Floor-to-ceiling glass walls open the living space to panoramic "
              "ocean views, and a private chef can be arranged on request."),
    dict(name="Skyline Penthouse", room_type="Penthouse", price=890, guests=4, beds=2, bedrooms=2,
         size=140, units=1, featured=True,
         short="Top-floor penthouse with a wraparound terrace and rooftop jacuzzi.",
         desc="Perched on the top floor, the Skyline Penthouse delivers 270-degree views "
              "of the coastline and city skyline. The wraparound terrace houses a private "
              "jacuzzi, outdoor dining set, and a lounge area — the ultimate space for "
              "watching the sunset."),
    dict(name="Classic Twin Room", room_type="Standard", price=119, guests=2, beds=2, bedrooms=1,
         size=24, units=15,
         short="Comfortable twin room, perfect for friends or colleagues travelling together.",
         desc="A well-appointed twin room with two double beds, a functional work desk, "
              "and a modern bathroom with a rainfall shower. Simple, comfortable, and "
              "great value without compromising on our signature LuxStay linens and "
              "amenities."),
    dict(name="Harbor View Deluxe", room_type="Deluxe", price=199, guests=2, beds=1, bedrooms=1,
         size=34, units=10,
         short="Elegant deluxe room facing the marina, with a soaking tub.",
         desc="Overlooking the yacht-lined marina, this Harbor View Deluxe room pairs a "
              "freestanding soaking tub with a spacious king bed and a reading nook. "
              "A great base for exploring the boardwalk and waterfront restaurants."),
    dict(name="Family Garden Suite", room_type="Suite", price=299, guests=5, beds=3, bedrooms=2,
         size=58, units=5,
         short="Two-bedroom suite designed for families, with a kids' bunk nook.",
         desc="Designed with families in mind, this two-bedroom suite includes a bunk "
              "nook for children, a shared lounge with a games console, and a garden-facing "
              "terrace. Connecting doors and childproof outlets throughout."),
    dict(name="Honeymoon Infinity Room", room_type="Suite", price=349, guests=2, beds=1, bedrooms=1,
         size=40, units=4, featured=True,
         short="Romantic suite with a private plunge pool and champagne welcome.",
         desc="Designed for celebrations, the Honeymoon Infinity Room includes a private "
              "plunge pool on the terrace, a four-poster canopy bed, and a complimentary "
              "bottle of champagne on arrival. Rose petal turndown available on request."),
]

AMENITIES = [
    ("Free Wi-Fi", "wifi"), ("Infinity Pool Access", "pool"), ("Free Parking", "parking"),
    ("Spa Access", "spa"), ("Fitness Center", "gym"), ("Mini Bar", "bar"),
    ("Breakfast Included", "breakfast"), ("Air Conditioning", "ac"), ("Smart TV", "tv"),
    ("Pet Friendly", "pet"), ("Ocean View", "view"),
]

FAQS = [
    ("What time is check-in and check-out?", "Check-in is from 3:00 PM and check-out is by 11:00 AM. "
     "Early check-in and late check-out can be arranged, subject to availability, for a small fee."),
    ("Is breakfast included in the room rate?", "Breakfast is included for Suite, Villa, and Penthouse "
     "bookings. Standard and Deluxe rooms can add breakfast during checkout for $22 per person."),
    ("Can I cancel or modify my booking?", "Bookings can be cancelled free of charge up to 48 hours "
     "before check-in from your account's booking history page. Modifications can be requested via "
     "our contact form."),
    ("Do you offer airport transfers?", "Yes — private airport transfers can be arranged for an "
     "additional fee. Please contact our concierge at least 24 hours before arrival."),
    ("Is parking available on-site?", "Complimentary self-parking and valet parking are both "
     "available for all registered guests."),
    ("Are pets allowed?", "We welcome pets in our Garden View Suites and Villas for a nightly pet fee. "
     "Please let us know in advance so we can prepare the room."),
]

GALLERY_CAPTIONS = [
    ("Infinity Pool at Sunset", "Pool"), ("Lobby & Lounge", "Interior"), ("Presidential Villa Terrace", "Rooms"),
    ("Oceanfront Spa Suite", "Spa"), ("Rooftop Bar", "Dining"), ("Private Beach Access", "Beach"),
    ("Garden Courtyard", "Exterior"), ("Chef's Tasting Menu", "Dining"), ("Fitness Center", "Wellness"),
    ("Sunrise from the Penthouse", "Rooms"),
]

TESTIMONIAL_TEXTS = [
    "Absolutely stunning property — the staff anticipated every need before we even asked. "
    "We are already planning our next trip back.",
    "The villa exceeded every expectation. Waking up to that view with coffee on the terrace "
    "is something we'll never forget.",
    "Impeccable service from check-in to check-out. The spa treatments were the highlight of "
    "our anniversary trip.",
    "Room was spotless, the bed was incredibly comfortable, and the breakfast spread was "
    "restaurant-quality every single morning.",
    "Booking was seamless and the confirmation email had everything we needed. Would "
    "recommend to anyone looking for a luxury coastal escape.",
    "The kids loved the bunk nook and pool, and we loved the peace and quiet on our private "
    "terrace. Perfect balance for a family trip.",
]

FIRST_NAMES = ["Amara", "Liam", "Sofia", "Noah", "Elena", "Marco", "Priya", "James", "Yuki", "Fatima",
                "Lucas", "Zara", "Daniel", "Nina", "Omar"]
LAST_NAMES = ["Bennett", "Sato", "Alvarez", "Novak", "Khan", "Rossi", "Larsen", "Osei", "Dubois", "Park"]


def _placeholder_image(path, size, color, label=""):
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    if label:
        text_color = tuple(max(0, c - 60) for c in color)
        draw.text((16, size[1] - 34), label, fill=text_color)
    img.save(path, quality=85)


def _make_placeholder(subfolder, seed_key, size=(1200, 800)):
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    random.seed(seed_key)
    color = tuple(random.randint(90, 200) for _ in range(3))
    filename = f"{slugify(seed_key)}-{random.randint(1000,9999)}.jpg"
    thumb_filename = filename.replace(".jpg", "_thumb.jpg")
    _placeholder_image(os.path.join(upload_dir, filename), size, color, seed_key[:24])
    _placeholder_image(os.path.join(upload_dir, thumb_filename), (480, 320), color)
    return f"{subfolder}/{filename}", f"{subfolder}/{thumb_filename}"


def run_seed():
    db.create_all()

    if User.query.filter_by(role="admin").first() is None:
        admin = User(full_name="Hotel Administrator", email="admin@luxstay-hotel.com", role="admin")
        admin.set_password("Admin@12345")
        db.session.add(admin)

    amenity_objs = {}
    for name, icon in AMENITIES:
        amenity = Amenity.query.filter_by(name=name).first()
        if not amenity:
            amenity = Amenity(name=name, icon=icon)
            db.session.add(amenity)
        amenity_objs[name] = amenity
    db.session.flush()

    if Room.query.count() == 0:
        for data in ROOM_DATA:
            slug = slugify(data["name"])
            room = Room(
                name=data["name"], slug=slug, room_type=data["room_type"],
                description=data["desc"], short_description=data["short"],
                price_per_night=data["price"], discount_percent=random.choice([0, 0, 0, 10, 15]),
                max_guests=data["guests"], beds=data["beds"], bedrooms=data["bedrooms"],
                size_sqm=data["size"], total_units=data["units"], is_featured=data.get("featured", False),
                is_active=True,
            )
            room.amenities = random.sample(list(amenity_objs.values()), k=random.randint(5, 8))
            db.session.add(room)
            db.session.flush()

            for i in range(4):
                filename, thumb = _make_placeholder("rooms", f"{data['name']} {i}")
                db.session.add(RoomImage(room_id=room.id, filename=filename, thumbnail_filename=thumb,
                                          alt_text=room.name, position=i))

    db.session.commit()

    if User.query.filter_by(role="customer").count() == 0:
        customers = []
        for first, last in zip(FIRST_NAMES, LAST_NAMES * 2):
            user = User(
                full_name=f"{first} {last}",
                email=f"{first.lower()}.{last.lower()}@example.com",
                role="customer", is_active=True,
            )
            user.set_password("Password123!")
            db.session.add(user)
            customers.append(user)
        db.session.commit()

        rooms = Room.query.all()
        today = date.today()
        for _ in range(40):
            user = random.choice(customers)
            room = random.choice(rooms)
            start_offset = random.randint(-60, 60)
            check_in = today + timedelta(days=start_offset)
            nights = random.randint(2, 7)
            check_out = check_in + timedelta(days=nights)
            status = BookingStatus.CONFIRMED.value
            if check_out < today:
                status = random.choice([BookingStatus.COMPLETED.value, BookingStatus.COMPLETED.value,
                                         BookingStatus.CANCELLED.value])
            price = room.effective_price
            booking = Booking(
                reference=generate_booking_reference(), user_id=user.id, room_id=room.id,
                check_in=check_in, check_out=check_out, guests=random.randint(1, room.max_guests),
                nights=nights, price_per_night=price, total_price=round(price * nights, 2),
                status=status,
            )
            db.session.add(booking)
            db.session.flush()

            if status == BookingStatus.COMPLETED.value and random.random() < 0.7:
                review = Review(
                    user_id=user.id, room_id=room.id, booking_id=booking.id,
                    rating=random.choice([4, 4, 5, 5, 5, 3]),
                    title=random.choice(["Wonderful stay", "Highly recommend", "Great value", "Loved it"]),
                    body=random.choice(TESTIMONIAL_TEXTS), is_approved=True,
                )
                db.session.add(review)

        db.session.commit()
        for room in rooms:
            room.recalculate_rating()
        db.session.commit()

    if FAQ.query.count() == 0:
        for i, (q, a) in enumerate(FAQS):
            db.session.add(FAQ(question=q, answer=a, category="General", position=i, is_published=True))

    if GalleryImage.query.count() == 0:
        for i, (caption, category) in enumerate(GALLERY_CAPTIONS):
            filename, thumb = _make_placeholder("gallery", caption)
            db.session.add(GalleryImage(filename=filename, thumbnail_filename=thumb, caption=caption,
                                         category=category, position=i, is_published=True))

    if Promotion.query.count() == 0:
        db.session.add(Promotion(
            title="Early Bird Escape", description="Book 30 days in advance and save on any Suite or Villa.",
            code="EARLY20", discount_percent=20, starts_on=date.today(),
            ends_on=date.today() + timedelta(days=180), is_active=True,
        ))
        db.session.add(Promotion(
            title="Extended Stay Bonus", description="Stay 5 nights or more and receive 15% off your total.",
            code="STAY15", discount_percent=15, starts_on=date.today(),
            ends_on=date.today() + timedelta(days=365), is_active=True,
        ))

    db.session.commit()
