"""SQLAlchemy data models."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from database import db

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

ROLE_ADMINISTRATOR = "Administrator"
ROLE_STAFF = "Staff"
ALL_ROLES = {ROLE_ADMINISTRATOR, ROLE_STAFF}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_list(text: str | None) -> list[str]:
    """Parse a JSON array string, or return a list with the raw text as fallback."""
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(s) for s in parsed if s]
    except (json.JSONDecodeError, ValueError):
        pass
    return [text]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Caregiver(db.Model):
    """A caregiver imported from the organisation's directory."""

    __tablename__ = "caregivers"
    __table_args__ = (db.UniqueConstraint("name", "phone", name="uq_caregiver_name_phone"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(64), nullable=False, index=True)
    situation = db.Column(db.Text, nullable=True)
    grants = db.Column(db.Text, nullable=True)    # stored as JSON array string
    needs = db.Column(db.Text, nullable=True)     # stored as JSON array string
    hobbies = db.Column(db.Text, nullable=True)   # stored as JSON array string
    language = db.Column(db.String(512), nullable=True, index=True)  # stored as JSON array string
    birthday = db.Column(db.Date, nullable=True, index=True)
    zbi = db.Column(db.Float, nullable=True, index=True)
    stress_level = db.Column(db.String(20), nullable=True, index=True)
    stress_score = db.Column(db.Integer, nullable=True)
    centre = db.Column(db.String(150), nullable=True, index=True)
    check_when = db.Column(db.Date, nullable=True, index=True)
    check_what = db.Column(db.Text, nullable=True)
    flag = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this caregiver for JSON responses, parsing stored JSON arrays."""
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "situation": self.situation,
            "grants": _parse_list(self.grants),
            "needs": _parse_list(self.needs),
            "hobbies": _parse_list(self.hobbies),
            "language": _parse_list(self.language),
            "birthday": self.birthday.isoformat() if self.birthday else None,
            "zbi": self.zbi,
            "stress_level": self.stress_level,
            "stress_score": self.stress_score,
            "centre": self.centre,
            "check_when": self.check_when.isoformat() if self.check_when else None,
            "check_what": self.check_what,
            "flag": self.flag,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class User(db.Model):
    """An authenticated staff member of the system."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=ROLE_STAFF)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and store the password using Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMINISTRATOR

    def to_dict(self) -> dict[str, Any]:
        """Serialize this user for JSON responses (no password hash)."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class Setting(db.Model):
    """A persistent application setting stored as a key-value pair."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)


class EmailNotification(db.Model):
    """Record of an email notification sent, used to prevent same-day duplicates."""

    __tablename__ = "email_notifications"

    id = db.Column(db.Integer, primary_key=True)
    caregiver_id = db.Column(db.Integer, nullable=True, index=True)  # nullable for test emails
    alert_type = db.Column(db.String(50), nullable=False, index=True)
    recipient = db.Column(db.String(512), nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_label = db.Column(db.Date, nullable=False, index=True)  # the calendar day this covers
    success = db.Column(db.Boolean, nullable=False, default=True)
    error = db.Column(db.Text, nullable=True)


class AuditLog(db.Model):
    """An immutable record of a significant action performed by a user."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=True)   # ID of the affected record, if any
    detail = db.Column(db.Text, nullable=True)          # Human-readable extra context
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "action": self.action,
            "record_id": self.record_id,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }
