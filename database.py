"""Database extension and initialization helpers."""

from __future__ import annotations

import logging
import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_database(app: object) -> None:
    """Initialise the database, create all tables, and seed defaults."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _seed_default_user()


def _seed_default_user() -> None:
    """Create a default Administrator account on first run.

    Credentials are read from environment variables so they can be overridden:
      SEED_FULL_NAME  (default: Admin)
      SEED_USERNAME   (default: admin)
      SEED_EMAIL      (default: admin@carecircle.local)
      SEED_PASSWORD   (default: carecircle1)
    """
    from models import ROLE_ADMINISTRATOR, User  # avoid circular import at module level

    if User.query.first():
        return  # at least one account already exists — nothing to do

    full_name = os.getenv("SEED_FULL_NAME", "Admin")
    username  = os.getenv("SEED_USERNAME",  "admin")
    email     = os.getenv("SEED_EMAIL",     "admin@carecircle.local")
    password  = os.getenv("SEED_PASSWORD",  "carecircle1")

    user = User(
        full_name=full_name,
        username=username,
        email=email,
        role=ROLE_ADMINISTRATOR,
        active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info("Default Administrator account created — username: %s", username)
