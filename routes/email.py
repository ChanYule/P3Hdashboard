"""Email administration routes — Administrator only."""

from __future__ import annotations

import os

from flask import Blueprint, jsonify

from utils.auth import require_admin

email_bp = Blueprint("email", __name__, url_prefix="/email")


@email_bp.post("/test")
@require_admin
def test_email():
    """Send a test email and return the result.

    Requires SMTP to be configured (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD,
    SMTP_FROM) and NOTIFICATION_EMAIL to be set.
    """
    from config import Config
    from services.email_service import email_service_from_config

    recipient = getattr(Config, "NOTIFICATION_EMAIL", None) or os.getenv("NOTIFICATION_EMAIL", "")
    if not recipient:
        return jsonify({
            "success": False,
            "error": "NOTIFICATION_EMAIL is not configured. Set it in your environment variables.",
        }), 400

    svc = email_service_from_config(Config)
    if svc is None:
        return jsonify({
            "success": False,
            "error": (
                "SMTP is not fully configured. Ensure SMTP_HOST, SMTP_USERNAME, "
                "SMTP_PASSWORD and SMTP_FROM are set in your environment variables."
            ),
        }), 400

    ok = svc.send_test_email(recipient)
    if ok:
        return jsonify({"success": True, "message": f"Test email sent to {recipient}."}), 200
    return jsonify({
        "success": False,
        "error": "Failed to deliver the test email. Check application logs for details.",
    }), 502
