from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail


def send_email(subject, recipients, template, **context):
    """
    Renders templates/emails/<template>.html and .txt and sends it.
    In dev, MAIL_SUPPRESS_SEND=1 means Flask-Mail records the message
    without actually connecting to an SMTP server.
    """
    msg = Message(subject=subject, recipients=recipients, sender=current_app.config["MAIL_DEFAULT_SENDER"])
    msg.body = render_template(f"emails/{template}.txt", **context)
    msg.html = render_template(f"emails/{template}.html", **context)
    try:
        mail.send(msg)
    except Exception as exc:  # pragma: no cover - never block the request on email failure
        current_app.logger.warning("Email send failed: %s", exc)


def send_password_reset_email(user, reset_url):
    send_email(
        subject="Reset your LuxStay password",
        recipients=[user.email],
        template="password_reset",
        user=user,
        reset_url=reset_url,
    )


def send_booking_confirmation_email(booking):
    send_email(
        subject=f"Booking confirmed — {booking.reference}",
        recipients=[booking.user.email],
        template="booking_confirmation",
        booking=booking,
    )
