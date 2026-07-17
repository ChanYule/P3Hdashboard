"""Dashboard and analytics routes."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify

from models import Caregiver
from services.alert_service import grant_check_alerts, grant_followup_alerts, overdue_checkin_alerts, upcoming_birthdays
from services.analytics_service import analytics

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    """Return all dashboard counts and distributions in one JSON response."""
    data = analytics()
    caregivers = Caregiver.query.all()
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = Caregiver.query.filter(Caregiver.created_at >= month_start).count()
    stress = data.get("stress_distribution", {})
    grant_checks = grant_check_alerts()
    data.update({
        "total_caregivers": len(caregivers),
        "new_caregivers_this_month": new_this_month,
        "upcoming_birthdays": upcoming_birthdays(),
        "grant_followups_due": grant_followup_alerts(),
        "monthly_checkins_due": overdue_checkin_alerts(),
        "grant_checks_due": grant_checks,
        "stress_distribution": stress,
        "high_stress_count":     stress.get("High", 0),
        "moderate_stress_count": stress.get("Moderate", 0),
        "low_stress_count":      stress.get("Low", 0),
    })
    return jsonify(data)


@dashboard_bp.get("/analytics")
def analytics_report():
    """Return standalone analytics for charts and reporting."""
    return jsonify(analytics())


def _domains(caregivers: list[Caregiver]) -> dict[str, int]:
    """Estimate caregiving domains from situation text."""
    domains: dict[str, int] = {}
    for caregiver in caregivers:
        if caregiver.situation:
            for domain in ("Dementia", "Mobility", "Mental health", "Chronic illness"):
                if domain.lower() in caregiver.situation.lower():
                    domains[domain] = domains.get(domain, 0) + 1
    return domains
