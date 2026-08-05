import os
from flask import Flask, render_template
from config import config as config_map

from app.extensions import db, migrate, login_manager, csrf, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map[config_name])

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_context_processors(app)
    register_cli(app)

    return app


def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def register_blueprints(app):
    from app.hotel import hotel_bp
    from app.auth import auth_bp
    from app.booking import booking_bp
    from app.admin import admin_bp
    from app.api import api_bp

    app.register_blueprint(hotel_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(booking_bp, url_prefix="/booking")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def register_context_processors(app):
    from datetime import date
    from app.models import SiteSetting

    @app.context_processor
    def inject_globals():
        return {
            "HOTEL_NAME": app.config["HOTEL_NAME"],
            "HOTEL_PHONE": app.config["HOTEL_PHONE"],
            "HOTEL_EMAIL": app.config["HOTEL_EMAIL"],
            "HOTEL_ADDRESS": app.config["HOTEL_ADDRESS"],
            "HOTEL_LAT": app.config["HOTEL_LAT"],
            "HOTEL_LNG": app.config["HOTEL_LNG"],
            "today": date.today(),
            "get_setting": SiteSetting.get,
        }


def register_cli(app):
    @app.cli.command("seed-db")
    def seed_db():
        """Populate the database with realistic demo data."""
        from app.seed import run_seed

        run_seed()
        print("Database seeded.")

    @app.cli.command("create-admin")
    def create_admin():
        """Create an administrator account interactively."""
        import getpass
        from app.models import User

        email = input("Admin email: ").strip().lower()
        name = input("Full name: ").strip()
        password = getpass.getpass("Password: ")

        if User.query.filter_by(email=email).first():
            print("A user with that email already exists.")
            return

        user = User(email=email, full_name=name, role="admin", is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin account created for {email}.")
