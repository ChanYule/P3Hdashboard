# Caregiver Management System

A local Flask + SQLite backend with a built-in HTML/CSS/JS frontend for managing caregiver records, alerts, analytics, and workshop recommendations.

## Stack

- **Backend:** Python / Flask 3, SQLAlchemy, APScheduler
- **Database:** SQLite (`database/caregivers.db`, created automatically on first run)
- **Frontend:** Plain HTML/CSS/JS (`index.html`, `style.css`, `script.js`) served as static files by Flask

## Running the app

The workflow **Start application** runs `python app.py` and serves on port 5000.

```
python app.py
```

The database is created automatically. No migrations needed.

## Environment

- `SESSION_SECRET` — Replit secret used as Flask's `SECRET_KEY`.
- SMTP variables (`SMTP_HOST`, `SMTP_USERNAME`, etc.) are optional; email delivery is disabled if unset.
- `DATABASE_URL` from Replit's managed Postgres is intentionally ignored — the app always uses SQLite.

## Key routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | KPI counts, alerts, chart data |
| GET | `/caregivers` | Paginated/filtered caregiver list |
| GET | `/caregiver/<id>` | Full caregiver profile |
| POST | `/upload` | CSV/XLS/XLSX import |
| GET | `/alerts` | Birthdays, grant follow-ups, check-ins |
| POST | `/recommendations` | Workshop participant matching |
| GET | `/analytics` | Analytics report |

## Project structure

```
app.py              # App factory + entry point
config.py           # Config from env vars
database.py         # SQLAlchemy init
models.py           # ORM models
routes/             # Flask blueprints
services/           # Business logic
utils/              # Logging helpers
index.html          # Frontend SPA
style.css / script.js
```

## User preferences

- Keep SQLite; do not migrate to Replit's managed Postgres.
