"""Birthday, grant, and check-in alert rules."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

from models import Caregiver

logger = logging.getLogger(__name__)
GRANT_KEYWORDS = (
    "South West Community Caring Fund",
    "South West Caregiver Support Fund",
)


def _alert(caregiver: Caregiver, alert_type: str, message: str, due_date: date | None = None) -> dict[str, Any]:
    """Build a consistent alert payload."""
    return {"type": alert_type, "caregiver": caregiver.to_dict(), "message": message,
            "due_date": due_date.isoformat() if due_date else None}


def birthday_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return caregivers whose birthday falls today."""
    today = today or date.today()
    results = [_alert(c, "birthday", f"{c.name}'s birthday is today.")
               for c in Caregiver.query.filter(Caregiver.birthday.isnot(None)).all()
               if c.birthday.month == today.month and c.birthday.day == today.day]
    logger.info("Generated %d birthday alerts", len(results))
    return results


def upcoming_birthdays(days: int = 7, today: date | None = None) -> list[dict[str, Any]]:
    """Return birthdays in the next number of days, including today."""
    today = today or date.today()
    alerts = []
    for caregiver in Caregiver.query.filter(Caregiver.birthday.isnot(None)).all():
        occurrence = caregiver.birthday.replace(year=today.year)
        if occurrence < today:
            occurrence = occurrence.replace(year=today.year + 1)
        delta = (occurrence - today).days
        if 0 <= delta <= days:
            alerts.append(_alert(caregiver, "upcoming_birthday", f"Birthday in {delta} day(s).", occurrence))
    return sorted(alerts, key=lambda item: item["due_date"] or "")


def _grant_application_date(text: str) -> date | None:
    """Find the first common date format embedded in unstructured grant text."""
    match = re.search(r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b", text)
    if not match:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(match.group(), fmt).date()
        except ValueError:
            continue
    return None


def grant_followup_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return overdue 42-day follow-ups for supported grant text keywords."""
    today = today or date.today()
    alerts = []
    for caregiver in Caregiver.query.filter(Caregiver.grants.isnot(None)).all():
        text = caregiver.grants or ""
        if not any(keyword.lower() in text.lower() for keyword in GRANT_KEYWORDS):
            continue
        applied = _grant_application_date(text)
        if applied and (due := applied + timedelta(days=42)) <= today:
            alerts.append(_alert(caregiver, "grant_followup", "Grant follow-up is due.", due))
    logger.info("Generated %d grant follow-up alerts", len(alerts))
    return alerts


def overdue_checkin_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return caregivers whose configured check-in date is overdue."""
    today = today or date.today()
    caregivers = Caregiver.query.filter(Caregiver.check_when.isnot(None), Caregiver.check_when < today).all()
    results = [_alert(c, "monthly_checkin", "Monthly check-in is overdue.", c.check_when) for c in caregivers]
    logger.info("Generated %d overdue check-in alerts", len(results))
    return results


def all_alerts() -> dict[str, list[dict[str, Any]]]:
    """Return all current alert categories."""
    return {"birthdays_today": birthday_alerts(), "upcoming_birthdays": upcoming_birthdays(),
            "grant_followups": grant_followup_alerts(), "overdue_checkins": overdue_checkin_alerts()}
