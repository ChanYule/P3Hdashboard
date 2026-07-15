"""Alert API routes."""

from flask import Blueprint, jsonify

from services.alert_service import all_alerts

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.get("/alerts")
def get_alerts():
    """Return all presently actionable alert categories."""
    return jsonify(all_alerts())
