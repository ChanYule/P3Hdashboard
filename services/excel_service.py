"""Safe, idempotent caregiver spreadsheet import service."""

from __future__ import annotations

import json
import logging
import math
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from database import db
from models import Caregiver

logger = logging.getLogger(__name__)
REQUIRED_COLUMNS = {"Name", "Phone No"}
COLUMN_MAP = {
    "Name": "name", "Phone No": "phone", "Situation": "situation",
    "Grants": "grants", "Needs": "needs", "Hobbies": "hobbies",
    "Language": "language", "Birthday": "birthday", "ZBI": "zbi",
    "Centre": "centre", "Check When": "check_when", "Check What": "check_what",
    "Flag": "flag",
}


class ImportValidationError(ValueError):
    """Raised when an uploaded spreadsheet cannot be imported."""


def _value(value: Any) -> str | None:
    """Return a clean optional string for a dataframe value."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value).strip() or None


def _date_value(value: Any) -> date | None:
    """Convert a spreadsheet date value to a Python date, if valid."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if str(value).strip() == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def _gt_list(value: Any) -> str | None:
    """Parse "> item" formatted text into a JSON array string.

    Lines beginning with ">" are individual items. Falls back to
    comma-splitting, then stores the raw text as a single-item list.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return None
    # Try ">" line format
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            item = stripped[1:].strip()
            if item and item not in items:
                items.append(item)
    if items:
        return json.dumps(items)
    # Fallback: comma-separated
    comma_items = [piece.strip() for piece in text.split(",") if piece.strip()]
    if len(comma_items) > 1:
        return json.dumps(comma_items)
    # Single value
    return json.dumps([text])


def _comma_list(value: Any) -> str | None:
    """Parse a comma-separated string into a JSON array string."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return None
    seen: dict[str, None] = {}
    for item in text.split(","):
        item = item.strip()
        if item:
            seen[item] = None  # preserve order, deduplicate
    return json.dumps(list(seen)) if seen else None


def _zbi_value(value: Any) -> tuple[str | None, int | None, float | None]:
    """Parse a ZBI cell like 'High (68)' into (stress_level, stress_score, zbi_float)."""
    if value is None:
        return None, None, None
    try:
        if pd.isna(value):
            return None, None, None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return None, None, None
    # "High (68)" / "High Stress (10)" / "Moderate (45)" / "Low (18)" etc.
    m = re.match(r"^(High|Moderate|Low)(?:\s+Stress)?\s*\((\d+)\)$", text, re.IGNORECASE)
    if m:
        level = m.group(1).capitalize()
        score = int(m.group(2))
        return level, score, float(score)
    # Pure number
    try:
        num = float(text)
        if not math.isnan(num):
            score = int(num)
            return None, score, num
    except (TypeError, ValueError):
        pass
    # Pure label
    lower = text.lower()
    if lower in ("high", "moderate", "low"):
        return text.capitalize(), None, None
    return None, None, None


def import_caregivers(file_path: Path) -> dict[str, Any]:
    """Import caregivers from a CSV/XLS/XLSX file and upsert by name and phone."""
    started = time.perf_counter()
    extension = file_path.suffix.lower()
    if extension not in {".csv", ".xls", ".xlsx"}:
        raise ImportValidationError("Only .csv, .xls, and .xlsx files are supported.")
    try:
        frame = pd.read_csv(file_path) if extension == ".csv" else pd.read_excel(file_path)
    except Exception as exc:
        raise ImportValidationError("The uploaded file is not a readable spreadsheet.") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ImportValidationError(f"Missing required columns: {', '.join(sorted(missing))}.")
    if frame.empty:
        raise ImportValidationError("The uploaded spreadsheet contains no records.")

    imported = updated = skipped = 0
    last_names: list[str] = []

    for _, row in frame.iterrows():
        name = _value(row.get("Name"))
        phone = _value(row.get("Phone No"))
        if not name or not phone:
            skipped += 1
            continue
        # Skip rows with unparsable date values to avoid silent data loss.
        invalid_date = any(
            source in frame.columns and _value(row[source]) and _date_value(row[source]) is None
            for source in ("Birthday", "Check When")
        )
        if invalid_date:
            skipped += 1
            logger.warning("Skipped row with invalid date: name=%s", name)
            continue

        payload: dict[str, Any] = {}
        for source, target in COLUMN_MAP.items():
            if source not in frame.columns:
                continue
            val = row[source]
            if target in {"birthday", "check_when"}:
                payload[target] = _date_value(val)
            elif target == "zbi":
                level, score, zbi_float = _zbi_value(val)
                payload["zbi"] = zbi_float
                payload["stress_level"] = level
                payload["stress_score"] = score
            elif target in {"hobbies", "grants", "needs"}:
                payload[target] = _gt_list(val)
            elif target == "language":
                payload[target] = _comma_list(val)
            else:
                payload[target] = _value(val)

        caregiver = Caregiver.query.filter_by(name=name, phone=phone).one_or_none()
        if caregiver:
            for field, value in payload.items():
                setattr(caregiver, field, value)
            updated += 1
        else:
            db.session.add(Caregiver(**payload))
            imported += 1
        last_names.append(name)

    db.session.commit()

    # Return first 10 most recently touched records for the import preview.
    preview_query = Caregiver.query.order_by(Caregiver.updated_at.desc()).limit(10).all()
    preview = [c.to_dict() for c in preview_query]

    result: dict[str, Any] = {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "preview": preview,
    }
    logger.info("Spreadsheet imported: %s", {k: v for k, v in result.items() if k != "preview"})
    return result
