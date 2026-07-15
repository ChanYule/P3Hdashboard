"""Flask application factory for the local Caregiver Management System."""

from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify

from config import BASE_DIR, Config
from database import init_database
from routes.alerts import alerts_bp
from routes.caregivers import caregivers_bp
from routes.dashboard import dashboard_bp
from routes.recommendations import recommendations_bp
from routes.upload import upload_bp
from services.alert_service import birthday_alerts
from utils.logging import configure_logging


def create_app() -> Flask:
    """Create and configure the Flask application and its local dependencies."""
    configure_logging(BASE_DIR)
    app = Flask(__name__)
    app.config.from_object(Config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(BASE_DIR / "database").mkdir(exist_ok=True)
    init_database(app)
    for blueprint in (dashboard_bp, caregivers_bp, upload_bp, alerts_bp, recommendations_bp):
        app.register_blueprint(blueprint)
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
    app.run(host="127.0.0.1", port=5000, debug=False)
