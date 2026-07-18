"""Database extension and initialization helpers."""

from __future__ import annotations

import logging
import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_database(app: object) -> None:
    """Create all local SQLite tables, apply schema migrations, and seed defaults."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _migrate(app)
        _seed_default_user()


def _seed_default_user() -> None:
    """Create a default admin account on first run (or if all users are deleted).

    Credentials are read from environment variables so they can be overridden:
      SEED_FULL_NAME  (default: Admin)
      SEED_USERNAME   (default: admin)
      SEED_EMAIL      (default: admin@carecircle.local)
      SEED_PASSWORD   (default: carecircle1)
    """
    from models import User  # avoid circular import at module level

    if User.query.first():
        return  # at least one account already exists — nothing to do

    full_name = os.getenv("SEED_FULL_NAME", "Admin")
    username  = os.getenv("SEED_USERNAME",  "admin")
    email     = os.getenv("SEED_EMAIL",     "admin@carecircle.local")
    password  = os.getenv("SEED_PASSWORD",  "carecircle1")

    user = User(full_name=full_name, username=username, email=email, role="Care Coordinator")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info("Default account created — username: %s", username)


def _migrate(app: object) -> None:
    """Add new columns to existing tables without losing data."""
    with app.app_context():
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)

        # Caregiver table migrations
        try:
            existing = {col["name"] for col in inspector.get_columns("caregivers")}
        except Exception:
            existing = set()

        caregiver_additions = [
            ("stress_level", "ALTER TABLE caregivers ADD COLUMN stress_level VARCHAR(20)"),
            ("stress_score", "ALTER TABLE caregivers ADD COLUMN stress_score INTEGER"),
        ]
        for col_name, sql in caregiver_additions:
            if col_name not in existing:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info("Migration applied: added column caregivers.%s", col_name)
                except Exception as exc:
                    db.session.rollback()
                    logger.warning("Migration skipped for caregivers.%s: %s", col_name, exc)
