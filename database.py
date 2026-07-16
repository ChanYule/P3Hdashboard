"""Database extension and initialization helpers."""

from __future__ import annotations

import logging

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_database(app: object) -> None:
    """Create all local SQLite tables and apply schema migrations."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _migrate(app)


def _migrate(app: object) -> None:
    """Add new columns to existing tables without losing data."""
    with app.app_context():
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        try:
            existing = {col["name"] for col in inspector.get_columns("caregivers")}
        except Exception:
            return  # Table doesn't exist yet; create_all handles it.
        additions = [
            ("stress_level", "ALTER TABLE caregivers ADD COLUMN stress_level VARCHAR(20)"),
            ("stress_score", "ALTER TABLE caregivers ADD COLUMN stress_score INTEGER"),
        ]
        for col_name, sql in additions:
            if col_name not in existing:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info("Migration applied: added column %s", col_name)
                except Exception as exc:
                    db.session.rollback()
                    logger.warning("Migration skipped for %s: %s", col_name, exc)
