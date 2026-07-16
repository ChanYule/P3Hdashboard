"""Birthday, grant, and monthly check-in alert rules.

Alert logic for 'check_when' and 'check_what' columns:
  - IF check_what contains the word "Monthly"  → Monthly Check-in reminder
  - OTHERWISE                                   → Grant Follow-up reminder
Both use check_when as the due date.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from models import Caregiver

logger = logging.getLogger(__name__)


def _is_monthly(caregiver: Caregiver) -> bool:
    """Return True if this caregiver's check_what indicates a monthly check-in."""
    return bool(caregiver.check_what and "monthly" in caregiver.check_what.lower())


def _alert(caregiver: Caregiver, alert_type: str, message: str, due_date: date | None = None) -> dict[str, Any]:
    """Build a consistent alert payload."""
    return {
        "type": alert_type,
        "caregiver": caregiver.to_dict(),
        "message": message,
        "due_date": due_date.isoformat() if due_date else None,
    }


def birthday_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return caregivers whose birthday falls today."""
    today = today or date.today()
    results = [
        _alert(c, "birthday", f"{c.name}'s birthday is today.")
        for c in Caregiver.query.filter(Caregiver.birthday.isnot(None)).all()
        if c.birthday.month == today.month and c.birthday.day == today.day
    ]
    logger.info("Generated %d birthday alerts", len(results))
    return results


def upcoming_birthdays(days: int = 30, today: date | None = None) -> list[dict[str, Any]]:
    """Return birthdays in the next number of days, including today."""
    today = today or date.today()
    alerts = []
    for caregiver in Caregiver.query.filter(Caregiver.birthday.isnot(None)).all():
        occurrence = caregiver.birthday.replace(year=today.year)
        if occurrence < today:
            occurrence = occurrence.replace(year=today.year + 1)
        delta = (occurrence - today).days
        if 0 <= delta <= days:
            alerts.append(_alert(
                caregiver, "upcoming_birthday",
                f"Birthday in {delta} day(s)." if delta > 0 else "Birthday is today!",
                occurrence,
            ))
    return sorted(alerts, key=lambda item: item["due_date"] or "")


def grant_followup_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return caregivers whose check_when is due and check_what is NOT a monthly check-in.

    The 'check_when' column holds the follow-up date for grant-related reminders
    when 'check_what' does not contain the word 'Monthly'.
    """
    today = today or date.today()
    caregivers = Caregiver.query.filter(
        Caregiver.check_when.isnot(None),
        Caregiver.check_when <= today,
    ).all()
    results = [
        _alert(c, "grant_followup", "Grant follow-up is due.", c.check_when)
        for c in caregivers
        if not _is_monthly(c)
    ]
    logger.info("Generated %d grant follow-up alerts", len(results))
    return results


def overdue_checkin_alerts(today: date | None = None) -> list[dict[str, Any]]:
    """Return caregivers whose monthly check-in is overdue.

    Only caregivers whose 'check_what' contains the word 'Monthly' are considered
    monthly check-ins; all others are handled as grant follow-ups.
    """
    today = today or date.today()
    caregivers = Caregiver.query.filter(
        Caregiver.check_when.isnot(None),
        Caregiver.check_when <= today,
    ).all()
    results = [
        _alert(c, "monthly_checkin", "Monthly check-in is overdue.", c.check_when)
        for c in caregivers
        if _is_monthly(c)
    ]
    logger.info("Generated %d monthly check-in alerts", len(results))
    return results


def all_alerts() -> dict[str, list[dict[str, Any]]]:
    """Return all current alert categories."""
    return {
        "birthdays_today": birthday_alerts(),
        "upcoming_birthdays": upcoming_birthdays(),
        "grant_followups": grant_followup_alerts(),
        "overdue_checkins": overdue_checkin_alerts(),
    }
