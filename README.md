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

cp .env.example .env             # then edit values as needed
export FLASK_APP=run.py          # Windows: set FLASK_APP=run.py

flask db init                    # already generated in this repo — skip if migrations/ exists
flask db migrate -m "Initial schema"
flask db upgrade

flask seed-db                    # populates rooms, users, bookings, reviews, gallery, FAQs, promos
flask run
```

Visit `http://localhost:5000`.

**Seeded admin login:** `admin@luxstay-hotel.com` / `Admin@12345` — change this immediately in any real deployment, or run `flask create-admin` to create your own.

**Seeded customer login (any of these):** e.g. `amara.bennett@example.com` / `Password123!`

## SCSS

Source lives in `app/static/scss/`, organized as abstracts / base / layout / components / pages / themes / utilities, all pulled together by `main.scss`. Compile with [Dart Sass](https://sass-lang.com/):

```bash
npm install -g sass
sass app/static/scss/main.scss app/static/css/main.css --style=compressed --no-source-map
```

A compiled `app/static/css/main.css` is already checked in, so the app runs immediately without a build step — re-run the command above after editing any `.scss` file.

## Database migrations

This project uses Flask-Migrate (Alembic). After changing `app/models.py`:

```bash
flask db migrate -m "Describe the change"
flask db upgrade
```

## Deploying to Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render pointing at the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn run:app`
3. Create a Render **PostgreSQL** instance and attach it — Render sets `DATABASE_URL` automatically, which `config.py`'s `ProductionConfig` reads (and normalizes `postgres://` to `postgresql://`).
4. Set environment variables in the Render dashboard: `SECRET_KEY`, `FLASK_CONFIG=production`, and mail credentials if you want real emails to send (`MAIL_SUPPRESS_SEND=0`, `MAIL_USERNAME`, `MAIL_PASSWORD`).
5. After the first deploy, run migrations and seed data from a Render shell:
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
  seed.py      demo data generator
config.py      environment-based configuration
run.py         application entry point
```

## Notes on scope

The admin's content-management screens (Homepage, FAQ, Gallery, Promotions, Amenities) intentionally share a single generic CRUD pattern (form macros + one route per entity) rather than bespoke UI per entity — this keeps ~10 content types maintainable without hundreds of near-duplicate templates, while still being fully functional end to end.
