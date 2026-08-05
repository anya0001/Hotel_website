import secrets
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth_bp
from app.extensions import db, rate_limiter
from app.models import User
from app.forms import (
    RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm,
    ChangePasswordForm, ProfileForm
)
from app.email import send_password_reset_email
from app.utils import save_image, delete_image


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("hotel.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome to LuxStay, {user.full_name.split()[0]}!", "success")
        return redirect(url_for("hotel.home"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("hotel.home"))

    form = LoginForm()
    if form.validate_on_submit():
        if not rate_limiter.allow(f"login:{request.remote_addr}", max_hits=10, window_seconds=60):
            flash("Too many login attempts. Please wait a minute and try again.", "warning")
            return render_template("auth/login.html", form=form)

        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_url = request.args.get("next")
            flash(f"Welcome back, {user.full_name.split()[0]}!", "success")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard") if user.is_admin else url_for("hotel.home"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("hotel.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_password_reset_email(user, reset_url)
        # Always show the same message — never reveal whether an email exists.
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if request.method == "GET":
        form.full_name.data = current_user.full_name
        form.phone.data = current_user.phone

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None

        if form.avatar.data:
            try:
                filename, _ = save_image(form.avatar.data, subfolder="avatars")
                if current_user.avatar_url:
                    delete_image(current_user.avatar_url)
                current_user.avatar_url = filename
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("auth/profile.html", form=form)

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.profile"))

    return render_template("auth/change_password.html", form=form)
