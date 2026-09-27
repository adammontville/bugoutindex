# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
NYC DHS daily shelter census, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. HUD AHAR stays the annual national homelessness anchor. This
companion is New York City only. It is not a U.S. rate and it is not a
substitute for that anchor.

Source: NYC Open Data dataset ``k46n-sa2m`` (Department of Homeless
Services Daily Report). Verified 2026-09-27. The stored field is
``total_individuals_in_shelter``: single adults, people in adult
families, and adults and children in families with children in the DHS
shelter system on the census date. The sibling column
``total_individuals_in_families_with_children_in_shelter_`` is a subset
and is not used.

The census date is the source ``date_of_census`` calendar day. A Socrata
timestamp is reduced to ``YYYY-MM-DD``. This module does not stamp the
clock.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.redact import redact_secrets

DATASET_ID = "k46n-sa2m"
SODA_URL = "https://data.cityofnewyork.us/resource/k46n-sa2m.json"
SOURCE_URL = "https://data.cityofnewyork.us/Social-Services/DHS-Daily-Report/k46n-sa2m"
DATE_FIELD = "date_of_census"
# One total. Not the families-with-children subset (that field name has a
# trailing underscore and a narrower definition).
FIELD = "total_individuals_in_shelter"
SERIES = {
    "nyc_dhs_total_individuals": FIELD,
}
# About one quarter of the daily print, for the chart. The weekly CSV
# stores only the latest observation.
TRAILING_OBSERVATIONS = 90
TIMEOUT = 20


def _valid_day(value: object) -> Optional[str]:
    """Census date as ``YYYY-MM-DD``, or None if it is not one.

    Socrata sends ``2026-09-25T00:00:00.000``. The time is dropped. A
    value that is not a calendar day is dropped.
    """
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 10:
        return None
    day = text[:10]
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return None
    return day


def _count(value: object) -> Optional[int]:
    """Whole-person census count, or None if the cell is not one."""
    if value in ("", None, "."):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None
    if number != number.to_integral_value() or number < 0:
        return None
    return int(number)


def parse_rows(raw_rows: list) -> List[dict]:
    """Chronological census totals. Blank and non-numeric rows are dropped.

    The returned dates are census dates, not a fetch time. At most
    ``TRAILING_OBSERVATIONS`` points are kept (the newest ones).
    """
    points = []
    for row in raw_rows or []:
        if not isinstance(row, dict):
            continue
        day = _valid_day(row.get(DATE_FIELD))
        count = _count(row.get(FIELD))
        if day is None or count is None:
            continue
        points.append({"date": day, "value": count})
    points.sort(key=lambda item: item["date"])
    if len(points) > TRAILING_OBSERVATIONS:
        points = points[-TRAILING_OBSERVATIONS:]
    return points


def assemble(parsed: Dict[str, list], errors: List[str], message: str = "") -> dict:
    """Public payload. ``in_bugout_index`` is always false."""
    values: Dict[str, object] = {}
    dates: Dict[str, str] = {}
    observations: Dict[str, list] = {}
    for name in SERIES:
        rows = list(parsed.get(name) or [])
        observations[name] = rows
        if rows:
            values[name] = rows[-1]["value"]
            dates[name] = rows[-1]["date"]
        else:
            values[name] = None
    filled = [name for name, value in values.items() if value is not None]
    if len(filled) == len(SERIES) and not errors:
        status = "success"
    elif filled:
        status = "partial"
    else:
        status = "error"
    payload: Dict[str, object] = {
        "status": status,
        "in_bugout_index": False,
        "geography": "New York City",
        "scope": "NYC only; not a U.S. figure and not the HUD AHAR rate",
        "dataset_id": DATASET_ID,
        "source_url": SOURCE_URL,
        "series_ids": {name: SERIES[name] for name in SERIES},
        "reading": "total individuals in the NYC DHS shelter system",
        "values": values,
        "dates": dates,
        "observations": observations,
        "errors": list(errors),
    }
    if message:
        payload["message"] = message
    elif status == "error" and errors:
        payload["message"] = "; ".join(errors)
    return payload


def _raw_rows() -> list:
    params = {
        "$select": f"{DATE_FIELD},{FIELD}",
        "$order": f"{DATE_FIELD} DESC",
        "$limit": TRAILING_OBSERVATIONS + 14,
    }
    resp = get_with_retry(SODA_URL, params=params, timeout=TIMEOUT)
    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError("NYC Open Data response was not a list")
    return payload


def fetch() -> dict:
    parsed: Dict[str, list] = {}
    errors: List[str] = []
    name = next(iter(SERIES))
    try:
        parsed[name] = parse_rows(_raw_rows())
        if not parsed[name]:
            errors.append(f"{name}: no observations")
    except RetryError as exc:
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: NYC Open Data unreachable: {exc}"))
    except Exception as exc:  # noqa: BLE001
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: {exc}"))
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
