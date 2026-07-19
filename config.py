"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _pg_uri() -> str:
    """Return the PostgreSQL connection URI, normalising the scheme if needed."""
    url = os.getenv("DATABASE_URL", "")
    # Heroku / Replit may expose postgres:// — SQLAlchemy 1.4+ requires postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    """Base configuration for the CareCircle application."""

    SECRET_KEY: str = (
        os.getenv("SECRET_KEY")
        or os.getenv("SESSION_SECRET")
        or "change-this-in-production"
    )

    # PostgreSQL (Replit built-in); falls back to local SQLite only for dev convenience
    _pg = _pg_uri()
    SQLALCHEMY_DATABASE_URI: str = (
        _pg if _pg else f"sqlite:///{BASE_DIR / 'database' / 'caregivers.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024

    # Session inactivity timeout in minutes (default: 30)
    SESSION_INACTIVITY_MINUTES: int = int(os.getenv("SESSION_INACTIVITY_MINUTES", "30"))

    # SMTP (optional — email alerts)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    # Email notifications
    # Single address for now; comma-separate for multiple recipients
    NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
