"""Birthday, grant, and monthly check-in alert rules.

Alert logic for 'check_when' and 'check_what' columns:
  - IF check_what contains the word "Monthly"  → Monthly Check-in reminder
  - OTHERWISE                                   → Grant Follow-up reminder
Both use check_when as the due date.

Grant column alert logic:
  Each "> Applied for FUND on DATE (Check DATE)" line is parsed for a
  check date. Alerts are raised when the check date is within 30 days or past.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
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


def _parse_grant_date(date_str: str) -> date | None:
    """Parse flexible grant check-date strings: '31-Jul-26', '31-Jul-2026', etc."""
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y", "%d/%m/%y",
                "%d %B %Y", "%d-%B-%y", "%d-%B-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    try:
        import pandas as pd
        result = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
        if not pd.isna(result):
            return result.date()
    except Exception:
        pass
    return None


def _extract_fund_name(grant_text: str) -> str:
    """Pull the fund name from 'Applied for FUND on DATE (Check …)' text."""
    m = re.search(r"[Aa]pplied\s+for\s+(.+?)\s+on\s+", grant_text)
    if m:
        return m.group(1).strip()
    # fallback: strip the check-date clause and return what's left
    cleaned = re.sub(r"\(Check[^)]*\)", "", grant_text).strip().rstrip(" .,")
    return cleaned or grant_text


def _grant_checks_for(caregiver: Caregiver, today: date, window_days: int) -> list[dict[str, Any]]:
    """Parse a caregiver's grants field and return alerts for upcoming/overdue check dates."""
    if not caregiver.grants:
        return []
    try:
        grants = json.loads(caregiver.grants)
        if not isinstance(grants, list):
            return []
    except (json.JSONDecodeError, ValueError):
        return []

    alerts: list[dict[str, Any]] = []
    for grant_text in grants:
        check_match = re.search(r"\(Check\s+([^)]+)\)", grant_text, re.IGNORECASE)
        if not check_match:
            continue
        check_date = _parse_grant_date(check_match.group(1))
        if check_date is None:
            continue
        delta = (check_date - today).days
        if delta > window_days:
            continue          # too far away, skip
        fund_name = _extract_fund_name(grant_text)
        overdue = delta < 0
        msg = (
            f"Grant check overdue by {abs(delta)} day(s): {fund_name}"
            if overdue
            else f"Grant check due in {delta} day(s): {fund_name}"
            if delta > 0
            else f"Grant check due today: {fund_name}"
        )
        alerts.append(_alert(caregiver, "grant_check", msg, check_date))
    return alerts


def grant_check_alerts(today: date | None = None, window_days: int = 30) -> list[dict[str, Any]]:
    """Return alerts for check dates embedded in grant column entries.

    Parses lines like 'Applied for South West Caregiving Support Fund on
    19-June-2026 (Check 31-Jul-26)' for every caregiver and raises an alert
    when the check date is within *window_days* days or already past.
    """
    today = today or date.today()
    results: list[dict[str, Any]] = []
    for c in Caregiver.query.filter(Caregiver.grants.isnot(None)).all():
        results.extend(_grant_checks_for(c, today, window_days))
    results.sort(key=lambda a: a["due_date"] or "")
    logger.info("Generated %d grant check alerts", len(results))
    return results


def all_alerts() -> dict[str, list[dict[str, Any]]]:
    """Return all current alert categories."""
    return {
        "birthdays_today": birthday_alerts(),
        "upcoming_birthdays": upcoming_birthdays(),
        "grant_followups": grant_followup_alerts(),
        "overdue_checkins": overdue_checkin_alerts(),
        "grant_checks": grant_check_alerts(),
    }
