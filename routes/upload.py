"""Spreadsheet upload route."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from services.excel_service import ImportValidationError, import_caregivers

upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/upload")
def upload_file():
    """Store a temporary local spreadsheet and import its caregiver records."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "A spreadsheet file is required."}), 400
    name = secure_filename(file.filename)
    if Path(name).suffix.lower() not in {".csv", ".xls", ".xlsx"}:
        return jsonify({"error": "Only .csv, .xls, and .xlsx files are supported."}), 400
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / f"{uuid4().hex}_{name}"
    file.save(destination)
    try:
        return jsonify(import_caregivers(destination)), 201
    except ImportValidationError as exc:
        return jsonify({"error": str(exc)}), 400
