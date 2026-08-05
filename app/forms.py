from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, TextAreaField, IntegerField,
    DecimalField, SelectField, DateField, SelectMultipleField, HiddenField,
    widgets
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
)

from app.models import User


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")]
    )


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    avatar = FileField("Profile photo", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])


# ---------------------------------------------------------------------------
# Booking / public site
# ---------------------------------------------------------------------------

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class RoomSearchForm(FlaskForm):
    """Used both on the homepage widget and the /rooms search bar (GET)."""
    class Meta:
        csrf = False  # submitted as GET query string

    check_in = DateField("Check-in", validators=[Optional()])
    check_out = DateField("Check-out", validators=[Optional()])
    guests = IntegerField("Guests", validators=[Optional(), NumberRange(min=1, max=20)], default=2)
    room_type = StringField("Room type", validators=[Optional()])
    min_price = IntegerField("Min price", validators=[Optional(), NumberRange(min=0)])
    max_price = IntegerField("Max price", validators=[Optional(), NumberRange(min=0)])
    beds = IntegerField("Beds", validators=[Optional(), NumberRange(min=1)])
    amenities = MultiCheckboxField("Amenities", coerce=int, validators=[Optional()])
    sort = SelectField(
        "Sort by",
        choices=[
            ("recommended", "Recommended"),
            ("price_asc", "Price: Low to High"),
            ("price_desc", "Price: High to Low"),
            ("rating", "Highest Rated"),
        ],
        default="recommended",
        validators=[Optional()],
    )

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        if self.check_in.data and self.check_out.data:
            if self.check_out.data <= self.check_in.data:
                self.check_out.errors.append("Check-out must be after check-in.")
                return False
        return True


class BookingForm(FlaskForm):
    check_in = DateField("Check-in", validators=[DataRequired()])
    check_out = DateField("Check-out", validators=[DataRequired()])
    guests = IntegerField("Guests", validators=[DataRequired(), NumberRange(min=1, max=20)])
    special_requests = TextAreaField("Special requests", validators=[Optional(), Length(max=1000)])

    def validate_check_out(self, field):
        if self.check_in.data and field.data <= self.check_in.data:
            raise ValidationError("Check-out date must be after check-in date.")

    def validate_check_in(self, field):
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError("Check-in date cannot be in the past.")


class ReviewForm(FlaskForm):
    rating = SelectField(
        "Rating", choices=[(str(i), f"{i} star{'s' if i != 1 else ''}") for i in range(5, 0, -1)],
        validators=[DataRequired()]
    )
    title = StringField("Title", validators=[Optional(), Length(max=150)])
    body = TextAreaField("Your review", validators=[DataRequired(), Length(min=10, max=2000)])


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    subject = StringField("Subject", validators=[Optional(), Length(max=200)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=10, max=2000)])


class NewsletterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


# ---------------------------------------------------------------------------
# Admin - content management
# ---------------------------------------------------------------------------

class RoomForm(FlaskForm):
    name = StringField("Room name", validators=[DataRequired(), Length(max=120)])
    room_type = SelectField(
        "Room type",
        choices=[("Standard", "Standard"), ("Deluxe", "Deluxe"), ("Suite", "Suite"),
                 ("Villa", "Villa"), ("Penthouse", "Penthouse")],
        validators=[DataRequired()]
    )
    short_description = StringField("Short description", validators=[Optional(), Length(max=255)])
    description = TextAreaField("Full description", validators=[DataRequired()])
    price_per_night = DecimalField("Price per night", validators=[DataRequired(), NumberRange(min=0)])
    discount_percent = IntegerField("Discount %", validators=[Optional(), NumberRange(min=0, max=90)], default=0)
    max_guests = IntegerField("Max guests", validators=[DataRequired(), NumberRange(min=1, max=20)])
    beds = IntegerField("Beds", validators=[DataRequired(), NumberRange(min=1, max=10)])
    bedrooms = IntegerField("Bedrooms", validators=[Optional(), NumberRange(min=1, max=10)], default=1)
    size_sqm = IntegerField("Size (m²)", validators=[Optional(), NumberRange(min=1)])
    total_units = IntegerField("Total units in inventory", validators=[DataRequired(), NumberRange(min=1)])
    amenities = MultiCheckboxField("Amenities", coerce=int, validators=[Optional()])
    is_featured = BooleanField("Featured on homepage")
    is_active = BooleanField("Published / bookable", default=True)
    images = FileField(
        "Add images", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
        render_kw={"multiple": True}
    )


class AmenityForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)])
    icon = SelectField(
        "Icon", validators=[DataRequired()],
        choices=[
            ("wifi", "Wi-Fi"), ("pool", "Pool"), ("parking", "Parking"), ("spa", "Spa"),
            ("gym", "Gym"), ("bar", "Bar"), ("breakfast", "Breakfast"), ("ac", "Air conditioning"),
            ("tv", "TV"), ("pet", "Pet friendly"), ("view", "Ocean view"), ("check", "General"),
        ]
    )


class FAQForm(FlaskForm):
    question = StringField("Question", validators=[DataRequired(), Length(max=255)])
    answer = TextAreaField("Answer", validators=[DataRequired()])
    category = StringField("Category", validators=[Optional(), Length(max=60)], default="General")
    position = IntegerField("Display order", validators=[Optional()], default=0)
    is_published = BooleanField("Published", default=True)


class GalleryImageForm(FlaskForm):
    image = FileField("Image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    caption = StringField("Caption", validators=[Optional(), Length(max=255)])
    category = StringField("Category", validators=[Optional(), Length(max=60)], default="Hotel")
    position = IntegerField("Display order", validators=[Optional()], default=0)
    is_published = BooleanField("Published", default=True)


class PromotionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional()])
    code = StringField("Promo code", validators=[Optional(), Length(max=30)])
    discount_percent = IntegerField("Discount %", validators=[DataRequired(), NumberRange(min=1, max=90)])
    starts_on = DateField("Starts on", validators=[Optional()])
    ends_on = DateField("Ends on", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    image = FileField("Promo image", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])


class UserAdminForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    role = SelectField("Role", choices=[("customer", "Customer"), ("admin", "Administrator")])
    is_active = BooleanField("Active", default=True)


class HomepageSettingsForm(FlaskForm):
    hero_title = StringField("Hero title", validators=[DataRequired(), Length(max=200)])
    hero_subtitle = StringField("Hero subtitle", validators=[Optional(), Length(max=300)])
    stat_1_value = StringField("Stat 1 value", validators=[Optional(), Length(max=30)])
    stat_1_label = StringField("Stat 1 label", validators=[Optional(), Length(max=60)])
    stat_2_value = StringField("Stat 2 value", validators=[Optional(), Length(max=30)])
    stat_2_label = StringField("Stat 2 label", validators=[Optional(), Length(max=60)])
    stat_3_value = StringField("Stat 3 value", validators=[Optional(), Length(max=30)])
    stat_3_label = StringField("Stat 3 label", validators=[Optional(), Length(max=60)])
    stat_4_value = StringField("Stat 4 value", validators=[Optional(), Length(max=30)])
    stat_4_label = StringField("Stat 4 label", validators=[Optional(), Length(max=60)])


class BookingStatusForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[("pending", "Pending"), ("confirmed", "Confirmed"),
                 ("cancelled", "Cancelled"), ("completed", "Completed")]
    )


class DeleteForm(FlaskForm):
    """Bare CSRF-protected form used for delete/cancel buttons."""
    pass
