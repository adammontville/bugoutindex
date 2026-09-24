# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Food CPI year-over-year, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. The incubating note's 0–10% normalization is not implemented
here. That draft is not a score contribution.

The series is FRED ``CPIUFDNS``: Consumer Price Index for All Urban
Consumers, Food, U.S. city average, index 1982–84=100, not seasonally
adjusted. That is the FRED id for BLS ``CUUR0000SAF1``. FRED does not
publish ``CUUR0000SAF1`` or ``CUSR0000SAF1`` as series ids (those pages
404). The seasonally adjusted food index on FRED is ``CPIUFDSL`` (BLS
``CUSR0000SAF1``). It is not used.

BLS prints the 12-month food change from the not-seasonally-adjusted
index. That is the household-facing number (the CPI news release and the
BLS 12-month table). Seasonal adjustment is the 1-month convention, not
the 12-month public print. This module stores that 12-month percent
change, rounded half-up to one decimal so it matches the BLS table.
Observation dates are the FRED ``date`` of the later index month. This
module does not stamp the clock.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, List, Optional

from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.redact import redact_secrets
from runtime.util.secrets_compat import get_secret

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
# One primary series. The value stored under this name is the 12-month
# percent change, not the index level.
SERIES = {
    "food_cpi_yoy": "CPIUFDNS",
}
BLS_SERIES = {
    "food_cpi_yoy": "CUUR0000SAF1",
}
# Three years of the monthly public print, for the chart.
TRAILING_OBSERVATIONS = 36
# Index months to request: the chart window, twelve months of lookback,
# and a few extra rows so a FRED "." does not push a year-ago month out.
INDEX_LIMIT = TRAILING_OBSERVATIONS + 18
TIMEOUT = 20


def _valid_day(value: object) -> Optional[str]:
    """FRED observation date as ``YYYY-MM-DD``, or None if it is not one."""
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


def _year_ago(day: str) -> str:
    """Same month one year earlier. CPI food dates are the first of the month."""
    return f"{int(day[:4]) - 1}{day[4:]}"


def _public_yoy(current: object, prior: object) -> Optional[float]:
    """12-month percent change, half-up to one decimal (the BLS print)."""
    try:
        cur = Decimal(str(current).strip())
        prev = Decimal(str(prior).strip())
    except (InvalidOperation, AttributeError):
        return None
    if prev == 0:
        return None
    pct = ((cur - prev) / prev) * Decimal(100)
    return float(pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def parse_index(raw_observations: list) -> List[dict]:
    """Chronological index levels. Placeholder ``.`` rows are dropped.

    Values stay as the FRED text so the percent change is not a binary
    float of the index. Dates are FRED observation dates. The API limit
    is the bound; this does not trim to the chart window, because the
    year-ago month has to remain available.
    """
    points = []
    for obs in raw_observations or []:
        if not isinstance(obs, dict):
            continue
        day = _valid_day(obs.get("date", obs.get("observation_date")))
        if day is None:
            continue
        raw_value = obs.get("value")
        if raw_value in (".", "", None):
            continue
        text = str(raw_value).strip()
        try:
            Decimal(text)
        except InvalidOperation:
            continue
        points.append({"date": day, "value": text})
    points.sort(key=lambda row: row["date"])
    return points


def year_over_year(index_points: List[dict]) -> List[dict]:
    """Public 12-month percent changes from index levels.

    A month is kept only when both that month and the same month a year
    earlier are real FRED prints. The date on each point is the later
    observation. At most ``TRAILING_OBSERVATIONS`` points are kept.
    """
    by_date = {row["date"]: row["value"] for row in index_points or []}
    points = []
    for row in index_points or []:
        prior = by_date.get(_year_ago(row["date"]))
        if prior is None:
            continue
        value = _public_yoy(row["value"], prior)
        if value is None:
            continue
        points.append({"date": row["date"], "value": value})
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
        "series_ids": {name: SERIES[name] for name in SERIES},
        "bls_series_ids": {name: BLS_SERIES[name] for name in SERIES},
        "reading": "12-month percent change",
        "seasonal_adjustment": "not seasonally adjusted",
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


def _raw_observations(series_id: str, api_key: str) -> list:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": INDEX_LIMIT,
    }
    resp = get_with_retry(FRED_URL, params=params, timeout=TIMEOUT)
    return resp.json().get("observations", [])


def fetch() -> dict:
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return assemble({}, ["FRED_API_KEY not set"], message="FRED_API_KEY not set")

    parsed: Dict[str, list] = {}
    errors: List[str] = []
    for name, series_id in SERIES.items():
        try:
            index_points = parse_index(_raw_observations(series_id, api_key))
            parsed[name] = year_over_year(index_points)
            if not parsed[name]:
                errors.append(f"{name}: no observations")
        except RetryError as exc:
            parsed[name] = []
            errors.append(redact_secrets(f"{name}: FRED unreachable: {exc}"))
        except Exception as exc:  # noqa: BLE001
            parsed[name] = []
            errors.append(redact_secrets(f"{name}: {exc}"))
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
