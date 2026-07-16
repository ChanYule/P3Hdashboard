"""Account management routes — profile and password."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database import db
from models import User

account_bp = Blueprint("account", __name__, url_prefix="/account")


def _current_user() -> User | None:
    """Return the authenticated user or None."""
    user_id = session.get("user_id")
    return User.query.get(user_id) if user_id else None


@account_bp.get("")
def get_profile():
    """Return the current user's profile."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    return jsonify(user.to_dict())


@account_bp.put("")
def update_profile():
    """Update full name and/or email."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    if not full_name and not email:
        return jsonify({"error": "Provide at least one field to update."}), 400
    if full_name:
        user.full_name = full_name
    if email:
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            return jsonify({"error": "That email is already in use."}), 409
        user.email = email
    db.session.commit()
    return jsonify({"message": "Profile updated.", "user": user.to_dict()}), 200


@account_bp.post("/password")
def change_password():
    """Change the user's password after verifying the current one."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    data = request.get_json(silent=True) or {}
    current = str(data.get("current_password", ""))
    new_pw = str(data.get("new_password", ""))
    confirm = str(data.get("confirm_password", ""))
    if not all([current, new_pw, confirm]):
        return jsonify({"error": "All password fields are required."}), 400
    if not user.check_password(current):
        return jsonify({"error": "Current password is incorrect."}), 401
    if new_pw != confirm:
        return jsonify({"error": "New passwords do not match."}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400
    user.set_password(new_pw)
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200
