"""Database extension and initialization helpers."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_database(app: object) -> None:
    """Create all local SQLite tables inside the Flask application context."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
