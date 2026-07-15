"""Safe, idempotent caregiver spreadsheet import service."""

from __future__ import annotations

import logging
import math
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
    if value is None or pd.isna(value):
        return None
    return str(value).strip() or None


def _date_value(value: Any) -> date | None:
    """Convert a spreadsheet date value to a Python date, if valid."""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def _number_value(value: Any) -> float | None:
    """Convert a spreadsheet numeric value to float, if valid."""
    if value is None or pd.isna(value):
        return None
    try:
        parsed = float(value)
        return None if math.isnan(parsed) else parsed
    except (TypeError, ValueError):
        return None


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
    for _, row in frame.iterrows():
        name, phone = _value(row.get("Name")), _value(row.get("Phone No"))
        if not name or not phone:
            skipped += 1
            continue
        # A supplied but unparsable date is not silently stored as missing data.
        invalid_date = any(
            source in frame.columns and _value(row[source]) and _date_value(row[source]) is None
            for source in ("Birthday", "Check When")
        )
        if invalid_date:
            skipped += 1
            logger.warning("Skipped caregiver row with invalid date: name=%s", name)
            continue
        payload: dict[str, Any] = {}
        for source, target in COLUMN_MAP.items():
            if source not in frame.columns:
                continue
            payload[target] = (
                _date_value(row[source]) if target in {"birthday", "check_when"}
                else _number_value(row[source]) if target == "zbi" else _value(row[source])
            )
        caregiver = Caregiver.query.filter_by(name=name, phone=phone).one_or_none()
        if caregiver:
            for field, value in payload.items():
                setattr(caregiver, field, value)
            updated += 1
        else:
            db.session.add(Caregiver(**payload))
            imported += 1
    db.session.commit()
    result = {"imported": imported, "updated": updated, "skipped": skipped,
              "duration_seconds": round(time.perf_counter() - started, 3)}
    logger.info("Spreadsheet imported: %s", result)
    return result
