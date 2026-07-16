"""Explainable caregiver workshop recommendation engine."""

from __future__ import annotations

import json
from typing import Any

from models import Caregiver


def _contains(value: str | None, terms: list[str]) -> bool:
    """Check if any normalised search term occurs in a text field."""
    return bool(value and any(term.lower() in value.lower() for term in terms if term))


def _language_matches(raw: str | None, target: str) -> bool:
    """Check whether target language appears in a JSON-array or plain language field."""
    if not raw or not target:
        return False
    try:
        langs = json.loads(raw)
        if isinstance(langs, list):
            return any(target.lower() == lang.lower() for lang in langs)
    except (json.JSONDecodeError, ValueError):
        pass
    return target.lower() == raw.lower()


def recommend_caregivers(criteria: dict[str, Any]) -> list[dict[str, Any]]:
    """Score caregivers against workshop criteria and return ranked matches."""
    topic = str(criteria.get("workshop", "")).strip()
    interests = [str(item) for item in criteria.get("interests", [])]
    domain = str(criteria.get("caregiving_domain", "")).strip()
    language = str(criteria.get("language", "")).strip()
    centre = str(criteria.get("centre", "")).strip()
    terms = [topic, domain, *interests]
    matches = []
    for caregiver in Caregiver.query.all():
        score, reasons = 0, []
        if _contains(caregiver.situation, [topic, domain]):
            score += 50
            reasons.append("Caregiving situation matches the workshop topic")
        if _contains(caregiver.needs, terms):
            score += 30
            reasons.append("Support needs match the workshop topic")
        if _contains(caregiver.hobbies, terms):
            score += 20
            reasons.append("Interests are relevant to the workshop")
        if language and _language_matches(caregiver.language, language):
            score += 20
            reasons.append(f"Speaks {language}")
        if centre and caregiver.centre and caregiver.centre.lower() == centre.lower():
            score += 10
            reasons.append(f"Belongs to {caregiver.centre}")
        if score:
            matches.append({"caregiver": caregiver.to_dict(), "score": score, "reasons": reasons})
    maximum = max(1, int(criteria.get("maximum_participants", 10)))
    return sorted(matches, key=lambda item: (-item["score"], item["caregiver"]["name"]))[:maximum]
