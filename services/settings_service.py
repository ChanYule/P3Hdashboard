"""Application settings persistence using the PostgreSQL settings table."""

from __future__ import annotations

from typing import Any

from database import db

DEFAULTS: dict[str, str] = {
    "app_name": "CareCircle",
    "default_centre": "",
    "notify_birthdays": "true",
    "notify_grants": "true",
    "notify_checkins": "true",
    "notify_email": "false",
    "theme": "light",
    "accent_colour": "#2e7d6b",
}


def get_all() -> dict[str, Any]:
    """Return all settings merged with defaults."""
    from models import Setting
    stored = {s.key: s.value for s in Setting.query.all()}
    return {**DEFAULTS, **stored}


def save(data: dict[str, Any]) -> None:
    """Persist a dictionary of setting key-value pairs."""
    from models import Setting
    for key, value in data.items():
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()


def clear_caregivers() -> int:
    """Delete all caregiver records and return the count removed."""
    from models import Caregiver
    count = Caregiver.query.count()
    Caregiver.query.delete()
    db.session.commit()
    return count
