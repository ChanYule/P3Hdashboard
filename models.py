"""SQLAlchemy data models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from database import db


class Caregiver(db.Model):
    """A caregiver imported from the organisation's local directory."""

    __tablename__ = "caregivers"
    __table_args__ = (db.UniqueConstraint("name", "phone", name="uq_caregiver_name_phone"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(64), nullable=False, index=True)
    situation = db.Column(db.Text, nullable=True)
    grants = db.Column(db.Text, nullable=True)
    needs = db.Column(db.Text, nullable=True)
    hobbies = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(100), nullable=True, index=True)
    birthday = db.Column(db.Date, nullable=True, index=True)
    zbi = db.Column(db.Float, nullable=True, index=True)
    centre = db.Column(db.String(150), nullable=True, index=True)
    check_when = db.Column(db.Date, nullable=True, index=True)
    check_what = db.Column(db.Text, nullable=True)
    flag = db.Column(db.String(100), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this caregiver for JSON responses."""
        return {
            "id": self.id, "name": self.name, "phone": self.phone,
            "situation": self.situation, "grants": self.grants,
            "needs": self.needs, "hobbies": self.hobbies,
            "language": self.language,
            "birthday": self.birthday.isoformat() if self.birthday else None,
            "zbi": self.zbi, "centre": self.centre,
            "check_when": self.check_when.isoformat() if self.check_when else None,
            "check_what": self.check_what, "flag": self.flag,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
