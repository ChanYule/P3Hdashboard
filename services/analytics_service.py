"""Aggregate analytics for dashboard and reporting APIs."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from typing import Any

from models import Caregiver


def _distribution(values: list[str | None]) -> dict[str, int]:
    """Create a sorted distribution while ignoring blank values."""
    return dict(sorted(Counter(value for value in values if value).items()))


def _parse_json_list(value: str | None) -> list[str]:
    """Return items from a JSON-array string or fall back to comma-splitting."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(s).strip() for s in parsed if s]
    except (json.JSONDecodeError, ValueError):
        pass
    return [piece.strip() for piece in value.replace(";", ",").split(",") if piece.strip()]


def _json_list_distribution(values: list[str | None]) -> dict[str, int]:
    """Distribution from JSON-array text fields (hobbies, language, etc.)."""
    items = [item for value in values for item in _parse_json_list(value)]
    return _distribution(items)


def _stress_label(c: Caregiver) -> str | None:
    """Return a stress label from the stored level or derived from the ZBI score."""
    if c.stress_level:
        return c.stress_level
    if c.zbi is not None:
        if c.zbi >= 61:
            return "High"
        if c.zbi >= 41:
            return "Moderate"
        return "Low"
    return None


def analytics() -> dict[str, Any]:
    """Calculate all directory analytics in a single database pass."""
    caregivers = Caregiver.query.all()
    today = date.today()
    ages = [
        today.year - c.birthday.year
        - ((today.month, today.day) < (c.birthday.month, c.birthday.day))
        for c in caregivers if c.birthday
    ]
    groups = {"under_40": 0, "40_49": 0, "50_59": 0, "60_69": 0, "70_plus": 0}
    for age in ages:
        key = (
            "under_40" if age < 40 else
            "40_49" if age < 50 else
            "50_59" if age < 60 else
            "60_69" if age < 70 else
            "70_plus"
        )
        groups[key] += 1
    birthdays = Counter(str(c.birthday.month) for c in caregivers if c.birthday)
    stress_dist = _distribution([_stress_label(c) for c in caregivers])
    return {
        "language_distribution": _json_list_distribution([c.language for c in caregivers]),
        "centre_distribution": _distribution([c.centre for c in caregivers]),
        "birthday_by_month": dict(sorted(birthdays.items(), key=lambda item: int(item[0]))),
        "age_groups": groups,
        "interest_distribution": _json_list_distribution([c.hobbies for c in caregivers]),
        "needs_distribution": _json_list_distribution([c.needs for c in caregivers]),
        "stress_distribution": stress_dist,
        "high_zbi_count": sum(1 for c in caregivers if c.zbi is not None and c.zbi >= 40),
        "average_age": round(sum(ages) / len(ages), 1) if ages else None,
    }
