# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Prime-age labor utilization, shown beside the BugOut Index.

These series are not inputs. ``compute_index`` never reads them, and they
have no weight. The incubating essay's composite formula is not implemented
here; a backtest is still required before any v1.1 promotion.

FRED / BLS Current Population Survey, seasonally adjusted, ages 25–54:

* ``LNS12300060`` — Employment-Population Ratio, the standard prime-age EPOP
* ``LNS11300060`` — Labor Force Participation Rate, the matching prime-age rate

The not-seasonally-adjusted twins (``LNU02300060``, ``LNU01300060``) are not
used. The essay asks for the usual prime-age measures, and these are the
seasonally adjusted series FRED publishes under those names.

Observation dates are the FRED ``date`` field. This module does not stamp
the clock.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.secrets_compat import get_secret

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
# Insertion order is the on-site order: EPOP, then participation.
SERIES = {
    "prime_age_epop": "LNS12300060",
    "prime_age_lfpr": "LNS11300060",
}
# Three years of the monthly print, for the chart. The weekly CSV stores
# only the latest observation.
TRAILING_OBSERVATIONS = 36
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


def parse_observations(raw_observations: list) -> List[dict]:
    """Chronological real prints. Placeholder ``.`` rows are dropped.

    The returned dates are the FRED observation dates, not a fetch time.
    At most ``TRAILING_OBSERVATIONS`` points are kept (the newest ones).
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
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        points.append({"date": day, "value": value})
    points.sort(key=lambda row: row["date"])
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
        # A few extra rows so a trailing '.' does not crowd out a real print.
        "limit": TRAILING_OBSERVATIONS + 6,
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
            parsed[name] = parse_observations(_raw_observations(series_id, api_key))
            if not parsed[name]:
                errors.append(f"{name}: no observations")
        except RetryError as exc:
            parsed[name] = []
            errors.append(f"{name}: FRED unreachable: {exc}")
        except Exception as exc:  # noqa: BLE001
            parsed[name] = []
            errors.append(f"{name}: {exc}")
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
