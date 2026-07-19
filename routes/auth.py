"""User authentication routes — login, sign up, logout, current user."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database import db
from models import ROLE_STAFF, User
from utils.auth import log_action

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/signup")
def signup():
    """Register a new staff account (defaults to Staff role)."""
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", "")).strip()
    username = str(data.get("username", "")).strip().lower()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm = str(data.get("confirm_password", ""))

    if not all([full_name, username, email, password, confirm]):
        return jsonify({"error": "All fields are required."}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is already taken."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists."}), 409

    user = User(full_name=full_name, username=username, email=email, role=ROLE_STAFF, active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Account created. Please log in."}), 201


@auth_bp.post("/login")
def login():
    """Validate credentials and create a session."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password."}), 401
    if not user.active:
        return jsonify({"error": "This account has been deactivated. Please contact an administrator."}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    session.permanent = True
    session["user_id"] = user.id
    session["last_active"] = datetime.utcnow().isoformat()

    log_action("user_login", record_id=user.id, detail=f"User '{user.username}' logged in")

    return jsonify({"message": "Login successful.", "user": user.to_dict()}), 200


@auth_bp.post("/logout")
def logout():
    """End the current user session."""
    log_action("user_logout")
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@auth_bp.get("/me")
def me():
    """Return the currently authenticated user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated.", "redirect": "/login.html"}), 401
    user = User.query.get(user_id)
    if not user or not user.active:
        session.clear()
        return jsonify({"error": "User not found.", "redirect": "/login.html"}), 401
    return jsonify(user.to_dict()), 200
