"""Application settings persistence using the SQLite settings table."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from config import BASE_DIR
from database import db

DB_PATH = BASE_DIR / "database" / "caregivers.db"
BACKUP_DIR = BASE_DIR / "database" / "backups"

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


def export_database() -> Path:
    """Return the path to the live SQLite database file for download."""
    return DB_PATH


def clear_caregivers() -> int:
    """Delete all caregiver records and return the count removed."""
    from models import Caregiver
    count = Caregiver.query.count()
    Caregiver.query.delete()
    db.session.commit()
    return count


def create_backup() -> str:
    """Copy the database to the backups directory and return the backup filename."""
    from datetime import datetime
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"caregivers_backup_{stamp}.db"
    shutil.copy2(DB_PATH, dest)
    return dest.name


def list_backups() -> list[dict[str, Any]]:
    """Return metadata for all existing backups."""
    from datetime import datetime
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    for path in sorted(BACKUP_DIR.glob("*.db"), reverse=True):
        stat = path.stat()
        backups.append({
            "name": path.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return backups


def restore_backup(filename: str) -> None:
    """Overwrite the live database with a named backup file."""
    src = BACKUP_DIR / filename
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Backup not found: {filename}")
    # Validate it's actually a backup, not a path traversal attempt
    if not src.resolve().parent == BACKUP_DIR.resolve():
        raise ValueError("Invalid backup filename.")
    shutil.copy2(src, DB_PATH)
