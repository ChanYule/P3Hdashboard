"""Caregiver directory and profile routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from models import Caregiver

caregivers_bp = Blueprint("caregivers", __name__)


@caregivers_bp.get("/caregivers")
def list_caregivers():
    """Search, filter, sort, and paginate caregiver records."""
    query = Caregiver.query
    search = request.args.get("search", "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(
            Caregiver.name.ilike(pattern),
            Caregiver.phone.ilike(pattern),
            Caregiver.centre.ilike(pattern),
            Caregiver.hobbies.ilike(pattern),
            Caregiver.grants.ilike(pattern),
            Caregiver.language.ilike(pattern),
        ))
    text_filters = {
        "language": Caregiver.language,
        "centre": Caregiver.centre,
        "hobby": Caregiver.hobbies,
        "need": Caregiver.needs,
        "flag": Caregiver.flag,
        "stress_level": Caregiver.stress_level,
    }
    for parameter, column in text_filters.items():
        value = request.args.get(parameter, "").strip()
        if value:
            query = query.filter(column.ilike(f"%{value}%"))
    sort_by = request.args.get("sort_by", "name")
    direction = request.args.get("sort_direction", "asc").lower()
    column = getattr(Caregiver, sort_by, Caregiver.name)
    query = query.order_by(column.desc() if direction == "desc" else column.asc())
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [caregiver.to_dict() for caregiver in result.items],
        "pagination": {
            "page": result.page,
            "per_page": result.per_page,
            "total": result.total,
            "pages": result.pages,
        },
    })


@caregivers_bp.get("/caregiver/<int:caregiver_id>")
def caregiver_profile(caregiver_id: int):
    """Return a complete caregiver profile."""
    caregiver = Caregiver.query.get_or_404(caregiver_id, description="Caregiver not found.")
    return jsonify(caregiver.to_dict())
