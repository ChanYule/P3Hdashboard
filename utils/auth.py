"""Authentication helpers, role-based access decorators, and audit logging."""

from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Callable

from flask import jsonify, session

from database import db


# ---------------------------------------------------------------------------
# Current-user helper
# ---------------------------------------------------------------------------

def current_user():
    """Return the currently authenticated User, or None."""
    from models import User
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


# ---------------------------------------------------------------------------
# Role-based access decorators
# ---------------------------------------------------------------------------

def require_admin(f: Callable) -> Callable:
    """Restrict an endpoint to users with the Administrator role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from models import ROLE_ADMINISTRATOR
        user = current_user()
        if not user or not user.active:
            return jsonify({"error": "Authentication required."}), 401
        if user.role != ROLE_ADMINISTRATOR:
            return jsonify({"error": "Administrator access required."}), 403
        return f(*args, **kwargs)
    return decorated


def require_auth(f: Callable) -> Callable:
    """Restrict an endpoint to any authenticated active user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user or not user.active:
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def log_action(
    action: str,
    record_id: int | None = None,
    detail: str | None = None,
) -> None:
    """Append an audit log entry for the current session user.

    Commits immediately so the entry is persisted even if the caller rolls back
    a subsequent transaction.
    """
    from models import AuditLog
    user_id = session.get("user_id")
    entry = AuditLog(
        user_id=user_id,
        action=action,
        record_id=record_id,
        detail=detail,
        timestamp=datetime.utcnow(),
    )
    db.session.add(entry)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
