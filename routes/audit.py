"""Audit log API routes — Administrator only."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from models import AuditLog
from utils.auth import require_admin

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")


@audit_bp.get("/logs")
@require_admin
def get_audit_logs():
    """Return paginated audit log entries, newest first."""
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 50, type=int)))
    action_filter = request.args.get("action", "").strip()

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    result = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "items": [entry.to_dict() for entry in result.items],
        "pagination": {
            "page": result.page,
            "per_page": result.per_page,
            "total": result.total,
            "pages": result.pages,
        },
    })
