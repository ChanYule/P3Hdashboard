"""Workshop recommendation API routes."""

from flask import Blueprint, jsonify, request

from services.recommendation_service import recommend_caregivers

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.post("/recommendations")
def recommendations():
    """Return explainable workshop participant recommendations."""
    payload = request.get_json(silent=True) or {}
    if not payload.get("workshop"):
        return jsonify({"error": "'workshop' is required."}), 400
    try:
        matches = recommend_caregivers(payload)
    except (TypeError, ValueError):
        return jsonify({"error": "maximum_participants must be a valid number."}), 400
    return jsonify({"items": matches, "count": len(matches)})
