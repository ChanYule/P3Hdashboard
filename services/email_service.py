"""Reusable email integration; logs locally until SMTP delivery is enabled."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _log_email(kind: str, caregiver: dict[str, Any]) -> None:
    """Log a future email delivery request without exposing credentials."""
    logger.info("%s email queued for caregiver id=%s", kind, caregiver.get("id"))
    print(f"{kind} email would be sent to {caregiver.get('name', 'caregiver')}")


def send_birthday_email(caregiver: dict[str, Any]) -> None:
    """Queue/log a birthday notification."""
    _log_email("Birthday", caregiver)


def send_followup_email(caregiver: dict[str, Any]) -> None:
    """Queue/log a grant follow-up notification."""
    _log_email("Grant follow-up", caregiver)


def send_checkin_email(caregiver: dict[str, Any]) -> None:
    """Queue/log a monthly check-in notification."""
    _log_email("Check-in", caregiver)
