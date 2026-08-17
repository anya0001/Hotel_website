# LuxStay Hotel & Resort — Booking Platform

A production-quality hotel booking website: Flask + SQLAlchemy backend,
Jinja2 templates, and a fully custom SCSS design system (no Bootstrap/Tailwind).

## Stack

- **Backend:** Python, Flask (application-factory pattern, Blueprints), SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF/WTForms, Flask-Mail
- **Frontend:** HTML5, nested SCSS (compiled to a single `main.css`), vanilla ES6+ JavaScript — no frontend framework, no CSS framework
- **Database:** SQLite for local development, PostgreSQL in production
- **Server:** Gunicorn, Render-compatible

## Features

- Public site: animated hero + search widget, featured/popular rooms, amenities, photo gallery, testimonials, stats, nearby attractions, FAQ, newsletter signup, contact form
- Room search with date/guest/price/beds/amenity filters, sorting, and pagination
- Room detail pages with an image gallery, live availability calendar, guest reviews, map embed, and policies
- Real booking engine: server-side double-booking prevention based on per-room-type inventory (`total_units`), live price estimate, and a JSON availability API used by the booking form before submit
- Accounts: register/login/logout, forgot/reset password (emailed token), profile with avatar upload, change password, booking history (upcoming/past/cancelled), saved rooms (favorites), notifications, and review submission gated to guests who actually booked
- Admin panel: revenue/analytics dashboard with a live chart, and full CRUD for rooms (with multi-image upload + compression), bookings (status management), users, reviews (approve/hide/delete), gallery, amenities, promotions, FAQ, and homepage copy (hero + stats), plus a contact-message inbox
- Security: hashed passwords (Werkzeug), CSRF protection on every form (Flask-WTF), role-gated admin routes, parameterized queries via the ORM, secure session cookies, basic in-memory rate limiting on login/contact
- SEO: meta tags, Open Graph tags, `robots.txt`, dynamic `sitemap.xml`, semantic HTML, lazy-loaded images

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
export FLASK_APP=run.py          # Windows PowerShell: $env:FLASK_APP="run.py"

flask db upgrade
flask seed-db
flask run
```

Visit `http://localhost:5000`.

### Demo accounts

`flask seed-db` creates one admin account and several customer accounts for local development. Their passwords are never stored in the source code.

- To choose a password before seeding, set `DEMO_PASSWORD` in your `.env` file.
- If `DEMO_PASSWORD` is blank, the seed command generates a random password and prints it once in the terminal.
- The admin email created by the seed command is `admin@luxstay-hotel.com`.
- For production deployments, create your own administrator with `flask create-admin` instead of relying on seeded accounts.

**Do not use seeded/demo credentials in a production deployment.**

## Configuration

Copy `.env.example` to `.env` and change the values for your deployment.

### Local development

The default development configuration uses SQLite, so no external database is required. `DEV_DATABASE_URL` can be changed if you want to use another development database.

### Production

Set:

- `FLASK_CONFIG=production`
- `SECRET_KEY` to a long, unpredictable value
- `DATABASE_URL` to your PostgreSQL connection string

The application intentionally refuses to start in production when `SECRET_KEY` or `DATABASE_URL` is missing. This prevents accidentally deploying with a known development secret or an unintended SQLite database.

### Hotel information

The following values can be customized through `.env` without editing Python code:

- `HOTEL_NAME`
- `HOTEL_PHONE`
- `HOTEL_EMAIL`
- `HOTEL_ADDRESS`
- `HOTEL_LAT`
- `HOTEL_LNG`

These values are exposed to the Jinja templates as `HOTEL_*` configuration variables.

### Email

Email sending is disabled by default for local development. Configure `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`, then set `MAIL_SUPPRESS_SEND=0` when you want real booking and password-reset emails to be delivered.

## SCSS

Source lives in `app/static/scss/`, organized as abstracts / base / layout / components / pages / themes / utilities, all pulled together by `main.scss`. Compile with [Dart Sass](https://sass-lang.com/):

```bash
npm install -g sass
sass app/static/scss/main.scss app/static/css/main.css --style=compressed --no-source-map
```

A compiled `app/static/css/main.css` is already checked in, so the app runs immediately without a build step — re-run the command above after editing any `.scss` file.

## Database migrations

This project uses Flask-Migrate (Alembic). The repository already includes the migration history, so a fresh install should use:

```bash
flask db upgrade
```

After changing `app/models.py` during development:

```bash
flask db migrate -m "Describe the change"
flask db upgrade
```

## Deploying to Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render pointing at the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn run:app`
3. Create a Render **PostgreSQL** instance and attach it — Render provides `DATABASE_URL` for the service.
4. Set `SECRET_KEY`, `FLASK_CONFIG=production`, and the hotel/mail environment variables in the Render dashboard.
5. After the first deploy, run migrations and create your own administrator from a Render shell:
   ```bash
   flask db upgrade
   flask create-admin
   ```

## Project structure

```
app/
  auth/        registration, login, password reset, profile
  admin/       role-gated admin panel (dashboard + CRUD)
  hotel/       public site (home, rooms, gallery, faq, contact)
  booking/     booking engine, favorites, reviews, notifications
  api/         JSON endpoints (availability, calendar)
  static/
    scss/      nested SCSS source (abstracts/base/layout/components/pages/themes/utilities)
    css/       compiled output (main.css)
    js/        vanilla JS (nav, gallery, room-detail widgets, admin chart, icons)
    images/    static assets + user uploads (images/uploads, git-ignored)
  templates/   Jinja2 templates, mirroring the blueprint structure, plus shared macros/emails/errors
  models.py    SQLAlchemy models
  forms.py     WTForms definitions
  utils.py     image upload/compression, slugify, booking reference generation
config.py      environment-based configuration
run.py         application entry point
```

## Notes on scope

The admin's content-management screens (Homepage, FAQ, Gallery, Promotions, Amenities) intentionally share a single generic CRUD pattern (form macros + one route per entity) rather than bespoke UI per entity — this keeps ~10 content types maintainable without hundreds of near-duplicate templates, while still being fully functional end to end.
