"""Flask application factory for the local Caregiver Management System."""

from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, request, send_from_directory, session

from config import BASE_DIR, Config
from database import init_database
from routes.account import account_bp
from routes.alerts import alerts_bp
from routes.auth import auth_bp
from routes.caregivers import caregivers_bp
from routes.dashboard import dashboard_bp
from routes.recommendations import recommendations_bp
from routes.settings_route import settings_bp
from routes.upload import upload_bp
from services.alert_service import birthday_alerts
from utils.logging import configure_logging

_PUBLIC_PATHS = {"/auth/login", "/auth/signup", "/login.html", "/signup.html"}
_STATIC_FILES = {"index.html", "style.css", "script.js", "login.html", "signup.html"}
_STATIC_DIRS = {"assets", "icons", "images"}


def create_app() -> Flask:
    """Create and configure the Flask application and its local dependencies."""
    configure_logging(BASE_DIR)
    app = Flask(__name__)
    app.config.from_object(Config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(BASE_DIR / "database").mkdir(exist_ok=True)
    init_database(app)

    blueprints = (
        auth_bp, account_bp, dashboard_bp, caregivers_bp,
        upload_bp, alerts_bp, recommendations_bp, settings_bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    @app.before_request
    def check_auth():
        """Redirect or reject unauthenticated requests."""
        path = request.path
        # Always allow public pages and auth endpoints
        if path in _PUBLIC_PATHS:
            return None
        # Always allow static assets (css, js, fonts, etc.)
        top = path.lstrip("/").split("/")[0]
        if top in _STATIC_DIRS or any(path.endswith(ext) for ext in (".css", ".js", ".ico", ".png", ".jpg", ".woff2")):
            return None
        # Check session
        if not session.get("user_id"):
            if path == "/" or not path.startswith("/auth"):
                if request.accept_mimetypes.accept_html and not path.startswith("/auth"):
                    return redirect("/login.html")
                return jsonify({"error": "Authentication required.", "redirect": "/login.html"}), 401

    @app.route("/")
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        top = filename.split("/")[0]
        if filename in _STATIC_FILES or top in _STATIC_DIRS:
            return send_from_directory(BASE_DIR, filename)
        return jsonify({"error": "Not found."}), 404

    _register_error_handlers(app)
    _start_scheduler(app)
    with app.app_context():
        alerts = birthday_alerts()
        logging.getLogger(__name__).info("Startup birthday check completed: %d alerts", len(alerts))
    return app


def _start_scheduler(app: Flask) -> None:
    """Schedule the daily birthday check without blocking application startup."""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(lambda: _daily_birthday_job(app), "cron", hour=8, minute=0, id="birthday_check")
    scheduler.start()
    app.extensions["scheduler"] = scheduler


def _daily_birthday_job(app: Flask) -> None:
    """Run the daily birthday check in the correct Flask context."""
    with app.app_context():
        birthday_alerts()


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
