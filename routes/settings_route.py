"""Settings API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file

import services.settings_service as svc

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.get("")
def get_settings():
    """Return all current settings."""
    return jsonify(svc.get_all())


@settings_bp.post("")
def save_settings():
    """Persist updated settings."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No settings provided."}), 400
    svc.save(data)
    return jsonify({"message": "Settings saved."}), 200


@settings_bp.get("/export")
def export_db():
    """Download the live SQLite database file."""
    path = svc.export_database()
    return send_file(path, as_attachment=True, download_name="caregivers_export.db")


@settings_bp.post("/clear")
def clear_db():
    """Delete all caregiver records."""
    count = svc.clear_caregivers()
    return jsonify({"message": f"Cleared {count} caregiver record(s).", "cleared": count}), 200


@settings_bp.post("/backup")
def create_backup():
    """Create a timestamped backup of the database."""
    name = svc.create_backup()
    return jsonify({"message": f"Backup created: {name}", "name": name}), 201


@settings_bp.get("/backups")
def list_backups():
    """List all existing database backups."""
    return jsonify({"backups": svc.list_backups()})


@settings_bp.post("/restore")
def restore_backup():
    """Restore the database from a named backup."""
    data = request.get_json(silent=True) or {}
    filename = str(data.get("filename", "")).strip()
    if not filename:
        return jsonify({"error": "Backup filename is required."}), 400
    try:
        svc.restore_backup(filename)
        return jsonify({"message": f"Database restored from {filename}."}), 200
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
