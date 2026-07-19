"""Flask application factory for the CareCircle Caregiver Management System."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, request, session

from config import BASE_DIR, Config
from database import init_database
from routes.account import account_bp
from routes.alerts import alerts_bp
from routes.audit import audit_bp
from routes.auth import auth_bp
from routes.caregivers import caregivers_bp
from routes.dashboard import dashboard_bp
from routes.email import email_bp
from routes.recommendations import recommendations_bp
from routes.settings_route import settings_bp
from routes.upload import upload_bp
from services.alert_service import birthday_alerts
from utils.logging import configure_logging

_PUBLIC_PATHS = {"/auth/login", "/auth/signup", "/login.html", "/signup.html"}
_STATIC_FILES = {"index.html", "style.css", "script.js", "login.html", "signup.html"}
_STATIC_DIRS = {"assets", "icons", "images"}


def create_app() -> Flask:
    """Create and configure the Flask application."""
    configure_logging(BASE_DIR)
    app = Flask(__name__)
    app.config.from_object(Config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    init_database(app)

    blueprints = (
        auth_bp, account_bp, dashboard_bp, caregivers_bp,
        upload_bp, alerts_bp, recommendations_bp, settings_bp,
        audit_bp, email_bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    _inactivity_timeout = timedelta(minutes=Config.SESSION_INACTIVITY_MINUTES)

    @app.before_request
    def check_auth():
        """Enforce authentication and session inactivity timeout."""
        path = request.path

        # Always allow public pages and auth endpoints
        if path in _PUBLIC_PATHS:
            return None

        # Always allow static assets
        top = path.lstrip("/").split("/")[0]
        if top in _STATIC_DIRS or any(
            path.endswith(ext) for ext in (".css", ".js", ".ico", ".png", ".jpg", ".woff2")
        ):
            return None

        user_id = session.get("user_id")
        if not user_id:
            if request.accept_mimetypes.accept_html and not path.startswith("/auth"):
                return redirect("/login.html")
            return jsonify({"error": "Authentication required.", "redirect": "/login.html"}), 401

        # Inactivity timeout check
        last_active_raw = session.get("last_active")
        if last_active_raw:
            try:
                last_active = datetime.fromisoformat(last_active_raw)
                if datetime.utcnow() - last_active > _inactivity_timeout:
                    session.clear()
                    if request.accept_mimetypes.accept_html:
                        return redirect("/login.html")
                    return jsonify({
                        "error": "Your session has expired due to inactivity.",
                        "redirect": "/login.html",
                    }), 401
            except ValueError:
                pass  # malformed timestamp — let the request through and refresh it

        # Refresh last-active timestamp on every authenticated request
        session["last_active"] = datetime.utcnow().isoformat()

    @app.route("/")
    def index():
        from flask import send_from_directory
        return send_from_directory(BASE_DIR, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        from flask import send_from_directory
        top = filename.split("/")[0]
        if filename in _STATIC_FILES or top in _STATIC_DIRS:
            return send_from_directory(BASE_DIR, filename)
        return jsonify({"error": "Not found."}), 404

    _register_error_handlers(app)
    _start_scheduler(app)

    with app.app_context():
        _check_email_service()
        alerts = birthday_alerts()
        logging.getLogger(__name__).info(
            "Startup birthday check completed: %d alerts", len(alerts)
        )

    return app


def _check_email_service() -> None:
    """Verify SMTP connectivity at startup and log the outcome."""
    from services.email_service import email_service_from_config
    svc = email_service_from_config(Config)
    if svc is None:
        logging.getLogger(__name__).info(
            "⚠ Email service unavailable — SMTP is not configured "
            "(set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM to enable)"
        )
        return
    svc.check_connection()


def _start_scheduler(app: Flask) -> None:
    """Schedule the daily notification job at 08:00."""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        lambda: _daily_notification_job(app),
        "cron", hour=8, minute=0,
        id="daily_notifications",
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler


def _daily_notification_job(app: Flask) -> None:
    """Run all alert generation and email delivery inside the Flask app context."""
    with app.app_context():
        from services.notification_service import run_daily_notifications
        summary = run_daily_notifications(app)
        logging.getLogger(__name__).info(
            "Daily notification job complete — %s", summary
        )


def _register_error_handlers(app: Flask) -> None:
    """Return JSON errors for common API failures."""

    @app.errorhandler(413)
    def file_too_large(error: Exception):
        return jsonify({"error": "File exceeds the configured upload size limit."}), 413

    @app.errorhandler(404)
    def not_found(error: Exception):
        return jsonify({"error": getattr(error, "description", "Resource not found.")}), 404

    @app.errorhandler(500)
    def internal_error(error: Exception):
        logging.getLogger(__name__).exception("Unhandled server error")
        return jsonify({"error": "An internal server error occurred."}), 500


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
