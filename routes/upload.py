"""Spreadsheet upload route — Administrator only."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from services.excel_service import ImportValidationError, import_caregivers
from utils.auth import log_action, require_admin

upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/upload")
@require_admin
def upload_file():
    """Store a temporary spreadsheet locally and import its caregiver records."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "A spreadsheet file is required."}), 400
    name = secure_filename(file.filename)
    if Path(name).suffix.lower() not in {".csv", ".xls", ".xlsx"}:
        return jsonify({"error": "Only .csv, .xls, and .xlsx files are supported."}), 400
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / f"{uuid4().hex}_{name}"
    file.save(destination)
    try:
        result = import_caregivers(destination)
        log_action(
            "excel_import",
            detail=f"Imported '{name}': {result.get('imported', 0)} new, {result.get('updated', 0)} updated",
        )
        return jsonify(result), 201
    except ImportValidationError as exc:
        return jsonify({"error": str(exc)}), 400
