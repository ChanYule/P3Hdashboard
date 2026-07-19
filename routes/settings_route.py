"""Settings API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

import services.settings_service as svc
from utils.auth import log_action, require_admin

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.get("")
def get_settings():
    """Return all current settings."""
    return jsonify(svc.get_all())


@settings_bp.post("")
@require_admin
def save_settings():
    """Persist updated settings (Administrator only)."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No settings provided."}), 400
    svc.save(data)
    log_action("settings_changed", detail=f"Keys updated: {', '.join(data.keys())}")
    return jsonify({"message": "Settings saved."}), 200


@settings_bp.post("/clear")
@require_admin
def clear_db():
    """Delete all caregiver records (Administrator only)."""
    count = svc.clear_caregivers()
    log_action("caregivers_cleared", detail=f"Deleted {count} caregiver record(s)")
    return jsonify({"message": f"Cleared {count} caregiver record(s).", "cleared": count}), 200


@settings_bp.get("/export")
@require_admin
def export_db():
    """Database export is not available for PostgreSQL deployments."""
    return jsonify({
        "error": "Direct database export is not supported in the shared PostgreSQL deployment. "
                 "Use your database provider's backup tools instead."
    }), 501


@settings_bp.post("/backup")
@require_admin
def create_backup():
    """Database backup is not available for PostgreSQL deployments."""
    return jsonify({
        "error": "File-based backups are not supported in the shared PostgreSQL deployment. "
                 "Use your database provider's backup tools instead."
    }), 501


@settings_bp.get("/backups")
@require_admin
def list_backups():
    """Database backup listing is not available for PostgreSQL deployments."""
    return jsonify({"backups": []})


@settings_bp.post("/restore")
@require_admin
def restore_backup():
    """Database restore is not available for PostgreSQL deployments."""
    return jsonify({
        "error": "File-based restore is not supported in the shared PostgreSQL deployment. "
                 "Use your database provider's backup tools instead."
    }), 501
