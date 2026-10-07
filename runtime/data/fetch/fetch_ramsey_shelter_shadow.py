# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Ramsey County emergency-shelter population, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. HUD AHAR stays the annual national homelessness anchor. This
companion is Ramsey County, Minnesota (the St. Paul area) only. It is not
a U.S. rate and it is not a substitute for that anchor.

Source: Ramsey County open data dataset ``9mck-bcqu`` (Emergency shelter
population and utilization). Verified 2026-10-07. Each row is one household
type for one month. The stored series sums ``population_enrollees`` ("Total
people") across the published household types for that month. A month is
kept only when all four published types are present, so a missing type
cannot silently shrink the total. ``utilization_rate`` and ``available_beds``
are not used.

The observation date is the source ``month_year`` calendar day (the first
of that month). This module does not stamp the clock.
"""
from __future__ import annotations

from typing import Dict, List

from runtime.data.fetch.shelter_shadow_common import assemble as _assemble
from runtime.data.fetch.shelter_shadow_common import valid_day, whole_count
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.redact import redact_secrets

DATASET_ID = "9mck-bcqu"
SODA_URL = "https://data.ramseycountymn.gov/resource/9mck-bcqu.json"
SOURCE_URL = (
    "https://data.ramseycountymn.gov/dataset/"
    "Emergency-shelter-population-and-utilization/9mck-bcqu"
)
DATE_FIELD = "month_year"
FIELD = "population_enrollees"
TYPE_FIELD = "family_type"
# Mutually exclusive household types on the dataset, verified 2026-10-07.
# A month missing one of these is dropped rather than published short.
REQUIRED_TYPES = frozenset({
    "Families",
    "Single Men",
    "Single Women",
    "Youth (18-24)",
})
SERIES = {
    "ramsey_shelter_total_people": FIELD,
}
# Two years of monthly points, for the chart. The weekly CSV stores only
# the latest observation.
TRAILING_OBSERVATIONS = 24
TIMEOUT = 20
GEOGRAPHY = "Ramsey County, Minnesota"
SCOPE = "Ramsey County only; not a U.S. figure and not the HUD AHAR rate"


def parse_rows(raw_rows: list) -> List[dict]:
    """Monthly totals. A month missing a required household type is dropped.

    Duplicate types in one month are dropped. The returned dates are the
    source month stamps, not a fetch time. At most
    ``TRAILING_OBSERVATIONS`` points are kept (the newest ones).
    """
    by_month: Dict[str, Dict[str, int]] = {}
    for row in raw_rows or []:
        if not isinstance(row, dict):
            continue
        day = valid_day(row.get(DATE_FIELD))
        count = whole_count(row.get(FIELD))
        kind = str(row.get(TYPE_FIELD) or "").strip()
        if day is None or count is None or not kind:
            continue
        bucket = by_month.setdefault(day, {})
        if kind in bucket:
            bucket["__duplicate__"] = 1
            continue
        bucket[kind] = count
    points = []
    for day in sorted(by_month):
        bucket = by_month[day]
        if bucket.get("__duplicate__"):
            continue
        kinds = {key for key in bucket if not key.startswith("__")}
        if not REQUIRED_TYPES.issubset(kinds):
            continue
        points.append({"date": day, "value": sum(bucket[key] for key in kinds)})
    if len(points) > TRAILING_OBSERVATIONS:
        points = points[-TRAILING_OBSERVATIONS:]
    return points


def assemble(parsed: Dict[str, list], errors: List[str], message: str = "") -> dict:
    """Public payload. ``in_bugout_index`` is always false."""
    return _assemble(
        SERIES,
        parsed,
        errors,
        geography=GEOGRAPHY,
        scope=SCOPE,
        dataset_id=DATASET_ID,
        source_url=SOURCE_URL,
        reading="total people in Ramsey County emergency shelters, summed across household types",
        message=message,
    )


def _raw_rows() -> list:
    params = {
        "$select": f"{DATE_FIELD},{TYPE_FIELD},{FIELD}",
        "$order": f"{DATE_FIELD} DESC",
        "$limit": 5000,
    }
    resp = get_with_retry(SODA_URL, params=params, timeout=TIMEOUT)
    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError("Ramsey County open data response was not a list")
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
        errors.append(redact_secrets(f"{name}: Ramsey County open data unreachable: {exc}"))
    except Exception as exc:  # noqa: BLE001
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: {exc}"))
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
