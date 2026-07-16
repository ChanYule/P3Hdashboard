"""User authentication routes — login, sign up, logout, current user."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, redirect, request, session

from database import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/signup")
def signup():
    """Register a new user account."""
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

    user = User(full_name=full_name, username=username, email=email, role="Care Coordinator")
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

    user.last_login = datetime.utcnow()
    db.session.commit()

    remember = bool(data.get("remember_me", False))
    session.permanent = remember
    session["user_id"] = user.id
    return jsonify({"message": "Login successful.", "user": user.to_dict()}), 200


@auth_bp.post("/logout")
def logout():
    """End the current user session."""
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@auth_bp.get("/me")
def me():
    """Return the currently authenticated user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated.", "redirect": "/login.html"}), 401
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({"error": "User not found.", "redirect": "/login.html"}), 401
    return jsonify(user.to_dict()), 200
