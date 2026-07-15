"""Aggregate analytics for dashboard and reporting APIs."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from models import Caregiver


def _distribution(values: list[str | None]) -> dict[str, int]:
    """Create a sorted distribution while ignoring blank values."""
    return dict(sorted(Counter(value for value in values if value).items()))


def _split_distribution(values: list[str | None]) -> dict[str, int]:
    """Create a distribution from comma/semicolon separated text fields."""
    items = [piece.strip() for value in values if value for piece in value.replace(";", ",").split(",")]
    return _distribution(items)


def analytics() -> dict[str, Any]:
    """Calculate all requested directory analytics in a single pass."""
    caregivers = Caregiver.query.all()
    today = date.today()
    ages = [today.year - c.birthday.year - ((today.month, today.day) < (c.birthday.month, c.birthday.day))
            for c in caregivers if c.birthday]
    groups = {"under_40": 0, "40_49": 0, "50_59": 0, "60_69": 0, "70_plus": 0}
    for age in ages:
        groups["under_40" if age < 40 else "40_49" if age < 50 else "50_59" if age < 60 else "60_69" if age < 70 else "70_plus"] += 1
    birthdays = Counter(str(c.birthday.month) for c in caregivers if c.birthday)
    return {"language_distribution": _distribution([c.language for c in caregivers]),
            "centre_distribution": _distribution([c.centre for c in caregivers]),
            "birthday_by_month": dict(sorted(birthdays.items(), key=lambda item: int(item[0]))),
            "age_groups": groups, "interest_distribution": _split_distribution([c.hobbies for c in caregivers]),
            "needs_distribution": _split_distribution([c.needs for c in caregivers]),
            "high_zbi_count": sum(1 for c in caregivers if c.zbi is not None and c.zbi >= 40),
            "average_age": round(sum(ages) / len(ages), 1) if ages else None}
