"""Orchestrates alert generation and multi-channel notification delivery.

Architecture
------------
NotificationService sits between the alert business logic (alert_service)
and the delivery channels (email_service, and future SMS/Teams/etc.).

Adding a new channel means adding a new method here and wiring it in;
no changes to alert_service or the route layer are needed.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


def _recipients_from_config(config: object) -> list[str]:
    """Return the list of notification recipients from the app config.

    Currently reads a single NOTIFICATION_EMAIL address. Designed to be
    extended to support per-centre routing or per-user preferences later.
    """
    import os
    # Check config attribute first, then fall back to env var directly
    email = getattr(config, "NOTIFICATION_EMAIL", None) or os.getenv("NOTIFICATION_EMAIL", "")
    if not email:
        return []
    # Future: return a list of addresses; for now a single address
    return [addr.strip() for addr in email.split(",") if addr.strip()]


def run_daily_notifications(app: object) -> dict[str, Any]:
    """Generate all alerts for today and send email notifications.

    Designed to be called from the APScheduler job inside an app context.
    Returns a summary dict with counts of sent/skipped/failed emails.

    Duplicate prevention: an EmailNotification record is written to the
    database the first time an email is sent for a given
    (caregiver_id, alert_type, date_label). Subsequent calls on the same
    day for the same caregiver+type are skipped.
    """
    from config import Config
    from models import EmailNotification
    from services import alert_service
    from services.email_service import email_service_from_config

    today = date.today()
    summary = {"sent": 0, "skipped": 0, "failed": 0, "email_disabled": False}

    recipients = _recipients_from_config(Config)
    if not recipients:
        logger.warning("Daily notifications skipped — NOTIFICATION_EMAIL is not configured")
        summary["email_disabled"] = True
        return summary

    svc = email_service_from_config(Config)
    if svc is None:
        logger.warning("Daily notifications skipped — SMTP is not configured")
        summary["email_disabled"] = True
        return summary

    # --- Collect all alert types ---
    jobs = [
        ("birthday",      alert_service.birthday_alerts(today),        "send_birthday_alert"),
        ("grant_followup", alert_service.grant_followup_alerts(today),  "send_grant_followup_alert"),
        ("monthly_checkin", alert_service.overdue_checkin_alerts(today), "send_checkin_alert"),
    ]

    for alert_type, alerts, method_name in jobs:
        for alert in alerts:
            cg = alert["caregiver"]
            cg_id = cg.get("id")
            result = _send_if_not_duplicate(
                svc=svc,
                method_name=method_name,
                caregiver=cg,
                alert_type=alert_type,
                recipients=recipients,
                today=today,
                caregiver_id=cg_id,
            )
            summary[result] += 1

    # --- Grant check alerts (with custom message) ---
    for alert in alert_service.grant_check_alerts(today):
        cg = alert["caregiver"]
        cg_id = cg.get("id")
        message = alert.get("message", "")
        result = _send_grant_check_if_not_duplicate(
            svc=svc,
            caregiver=cg,
            message=message,
            recipients=recipients,
            today=today,
            caregiver_id=cg_id,
        )
        summary[result] += 1

    logger.info(
        "Daily notifications complete — sent=%d skipped=%d failed=%d",
        summary["sent"], summary["skipped"], summary["failed"],
    )
    return summary


def _already_sent(caregiver_id: int | None, alert_type: str, today: date) -> bool:
    """Return True if an email was already sent for this caregiver+type today."""
    from models import EmailNotification
    from database import db
    exists = db.session.query(
        EmailNotification.query.filter_by(
            caregiver_id=caregiver_id,
            alert_type=alert_type,
            date_label=today,
        ).exists()
    ).scalar()
    return bool(exists)


def _record_sent(caregiver_id: int | None, alert_type: str, recipient: str, today: date, success: bool, error: str | None = None) -> None:
    """Write an EmailNotification record to prevent future duplicates."""
    from database import db
    from models import EmailNotification
    record = EmailNotification(
        caregiver_id=caregiver_id,
        alert_type=alert_type,
        recipient=recipient,
        sent_at=datetime.utcnow(),
        date_label=today,
        success=success,
        error=error,
    )
    db.session.add(record)
    db.session.commit()


def _send_if_not_duplicate(
    svc: Any,
    method_name: str,
    caregiver: dict,
    alert_type: str,
    recipients: list[str],
    today: date,
    caregiver_id: int | None,
) -> str:
    """Send via method_name, skipping if already sent today. Returns 'sent'|'skipped'|'failed'."""
    if _already_sent(caregiver_id, alert_type, today):
        logger.debug("Skipping %s for caregiver id=%s — already sent today", alert_type, caregiver_id)
        return "skipped"

    method = getattr(svc, method_name)
    ok = method(caregiver, recipients)
    _record_sent(caregiver_id, alert_type, ", ".join(recipients), today, ok)
    return "sent" if ok else "failed"


def _send_grant_check_if_not_duplicate(
    svc: Any,
    caregiver: dict,
    message: str,
    recipients: list[str],
    today: date,
    caregiver_id: int | None,
) -> str:
    alert_type = "grant_check"
    if _already_sent(caregiver_id, alert_type, today):
        logger.debug("Skipping grant_check for caregiver id=%s — already sent today", caregiver_id)
        return "skipped"

    ok = svc.send_grant_check_alert(caregiver, message, recipients)
    _record_sent(caregiver_id, alert_type, ", ".join(recipients), today, ok)
    return "sent" if ok else "failed"
