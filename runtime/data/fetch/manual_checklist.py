# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Read a person-maintained companion checklist.

The weekly job calls this for shadow series. It copies the cells a person
wrote. It does not fill a missing row, and it does not stamp the current time.
These rows are not inputs to ``compute_index``.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

COLUMNS = (
    "series",
    "value",
    "observation_period",
    "observation_date",
    "source",
    "source_url",
    "reviewed_at",
)

_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_FAKE_TIMESTAMPS = {
    "2025-01-01T00:00:00Z",
    "2025-01-01T00:00:00+00:00",
}


class ChecklistError(Exception):
    """The companion checklist cannot supply these series. Callers fail closed."""


def load_series(
    path: Path,
    *,
    required: Iterable[str],
    max_rows_per_series: int,
    label: str,
    value_kinds: Optional[Mapping[str, str]] = None,
) -> Dict[str, List[dict]]:
    """Return checklist points keyed by series, oldest first.

    A missing file, a missing required series, a blank value, a bad date,
    a timestamp, a duplicate date, an unknown series name, or too many rows
    raises ``ChecklistError``. Nothing here invents a number or a date.

    ``value_kinds`` maps a series to ``percent`` (0–100, the default) or
    ``count`` (a non-negative whole number, used for a local headcount).
    """
    required_names = tuple(required)
    kinds = dict(value_kinds or {})
    table = Path(path)
    rows = _read_rows(table, label)
    grouped: Dict[str, List[dict]] = {name: [] for name in required_names}
    allowed = set(required_names)
    for raw in rows:
        cleaned = {name: (raw.get(name) or "").strip() for name in COLUMNS}
        if not any(cleaned.values()):
            continue
        series = cleaned["series"]
        if series not in allowed:
            raise ChecklistError(
                f"{label} checklist has an unexpected series: {series or '(blank)'}"
            )
        grouped[series].append(
            _validate_row(label, series, cleaned, kinds.get(series, "percent"))
        )

    missing = [name for name in required_names if not grouped[name]]
    if missing:
        raise ChecklistError(
            f"{label} checklist is missing series: " + ", ".join(missing)
        )

    points: Dict[str, List[dict]] = {}
    for name in required_names:
        rows_for_series = grouped[name]
        if len(rows_for_series) > max_rows_per_series:
            raise ChecklistError(
                f"{label} checklist has {len(rows_for_series)} {name} rows; "
                f"keep at most {max_rows_per_series}"
            )
        dates = [row["observation_date"] for row in rows_for_series]
        if len(dates) != len(set(dates)):
            raise ChecklistError(
                f"{label} checklist repeats an observation_date for {name}"
            )
        rows_for_series.sort(key=lambda row: row["observation_date"])
        points[name] = rows_for_series
    return points


def build_payload(
    series_ids: Mapping[str, str],
    points: Mapping[str, list],
    errors: List[str],
    *,
    extra: Optional[dict] = None,
    message: str = "",
) -> dict:
    """Public companion payload. ``in_bugout_index`` is always false."""
    values: Dict[str, object] = {}
    dates: Dict[str, str] = {}
    periods: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    source_urls: Dict[str, str] = {}
    reviewed_at: Dict[str, str] = {}
    observations: Dict[str, list] = {}
    for name in series_ids:
        rows = list(points.get(name) or [])
        observations[name] = [
            {"date": row["observation_date"], "value": row["value"]} for row in rows
        ]
        if rows:
            latest = rows[-1]
            values[name] = latest["value"]
            dates[name] = latest["observation_date"]
            periods[name] = latest["observation_period"]
            sources[name] = latest["source"]
            source_urls[name] = latest["source_url"]
            reviewed_at[name] = latest["reviewed_at"]
        else:
            values[name] = None
    filled = [name for name, value in values.items() if value is not None]
    if len(filled) == len(series_ids) and not errors:
        status = "success"
    elif filled:
        status = "partial"
    else:
        status = "error"
    payload: Dict[str, object] = {
        "status": status,
        "in_bugout_index": False,
        "series_ids": {name: series_ids[name] for name in series_ids},
        "values": values,
        "dates": dates,
        "periods": periods,
        "sources": sources,
        "source_urls": source_urls,
        "reviewed_at": reviewed_at,
        "observations": observations,
        "errors": list(errors),
    }
    if extra:
        for key, value in extra.items():
            if key == "in_bugout_index":
                continue
            payload[key] = value
    payload["in_bugout_index"] = False
    if message:
        payload["message"] = message
    elif status == "error" and errors:
        payload["message"] = "; ".join(errors)
    return payload


def _read_rows(table: Path, label: str) -> list:
    if not table.is_file():
        raise ChecklistError(f"{label} checklist is missing: {table.name}")
    try:
        with table.open(newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
            missing = [name for name in COLUMNS if name not in header]
            if missing:
                raise ChecklistError(
                    f"{label} checklist is missing columns: " + ", ".join(missing)
                )
            return list(reader)
    except ChecklistError:
        raise
    except OSError as exc:
        raise ChecklistError(f"{label} checklist could not be read: {exc}") from exc


def _validate_row(label: str, series: str, cleaned: dict, value_kind: str = "percent") -> dict:
    for name in ("value", "observation_date", "reviewed_at"):
        text = cleaned[name]
        if text in _FAKE_TIMESTAMPS or "T" in text:
            raise ChecklistError(
                f"{label} {name} for {series} must be a date or number a person wrote, not a timestamp"
            )
    if value_kind == "percent":
        value = _percent(cleaned["value"], label, series)
    elif value_kind == "count":
        value = _count(cleaned["value"], label, series)
    else:
        raise ChecklistError(f"{label} has no value rule {value_kind} for {series}")
    if not cleaned["observation_period"]:
        raise ChecklistError(f"{label} observation_period for {series} is blank")
    observed = cleaned["observation_date"]
    if not _is_day(observed):
        raise ChecklistError(
            f"{label} observation_date for {series} must be YYYY-MM-DD"
        )
    if not cleaned["source"]:
        raise ChecklistError(f"{label} source for {series} is blank")
    url = cleaned["source_url"]
    if not url.startswith("https://"):
        raise ChecklistError(f"{label} source_url for {series} is not an https URL")
    reviewed = cleaned["reviewed_at"]
    if not _is_day(reviewed):
        raise ChecklistError(
            f"{label} reviewed_at for {series} must be the calendar date of the review (YYYY-MM-DD)"
        )
    if reviewed < observed:
        raise ChecklistError(
            f"{label} reviewed_at for {series} is earlier than observation_date"
        )
    return {
        "series": series,
        "value": value,
        "observation_period": cleaned["observation_period"],
        "observation_date": observed,
        "source": cleaned["source"],
        "source_url": url,
        "reviewed_at": reviewed,
    }


def _count(text: str, label: str, series: str):
    if not text:
        raise ChecklistError(f"{label} value for {series} is blank")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ChecklistError(f"{label} value for {series} is not a number") from None
    if number != number.to_integral_value() or number < 0:
        raise ChecklistError(
            f"{label} value for {series} must be a non-negative whole number"
        )
    return int(number)


def _percent(text: str, label: str, series: str):
    if not text:
        raise ChecklistError(f"{label} value for {series} is blank")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ChecklistError(f"{label} value for {series} is not a number") from None
    if number < 0 or number > 100:
        raise ChecklistError(f"{label} value for {series} is outside 0–100")
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def _is_day(text: str) -> bool:
    if not _DAY.fullmatch(text):
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return True
