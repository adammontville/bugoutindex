# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
ALFRED-based revision history for nonfarm payrolls (PAYEMS) and the
unemployment rate (UNRATE).

ALFRED is the St. Louis Fed's archive of every vintage of every series
in FRED. We use it to reconstruct what each monthly observation looked
like at three points in time:

    vintage_initial : the value as of the day BLS first published it
    vintage_first   : the value one month after initial release
    vintage_second  : the value two months after initial release

For PAYEMS, this is the canonical "first/second/third estimate"
sequence. The numbers commonly quoted in the press are the initial
release; the +1 and +2 vintages incorporate later survey responses and
small methodological adjustments.

For UNRATE, monthly revisions are rare; the meaningful revision is
the **annual benchmark** in January (which can shift the prior 5
years). To capture that, we record two vintages of the most recent
24 months: the **current** value (post-benchmark) and the value as it
stood **immediately before the most recent January benchmark**.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from runtime.util.http_retry import get_with_retry, RetryError
from runtime.util.secrets_compat import get_secret

FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"

# How many monthly observations to keep on the chart.
PAYEMS_WINDOW_MONTHS = 24
UNRATE_WINDOW_MONTHS = 60  # 5 years; benchmark revises 5y of history


# --- Data shape -------------------------------------------------------------

@dataclass
class RevisionRow:
    """One observation month with up to three vintage values."""
    observation_date: str       # YYYY-MM-01
    vintage_initial: Optional[float]
    vintage_first: Optional[float]
    vintage_second: Optional[float]
    initial_release_date: Optional[str] = None  # YYYY-MM-DD


# --- ALFRED query helpers ---------------------------------------------------

def _fetch_observation(
    series_id: str,
    obs_date: str,
    realtime_start: Optional[str] = None,
    realtime_end: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """
    Fetch a single observation for `obs_date`, optionally as it was on
    `realtime_start`. Returns {'value': float, 'realtime_start': '...',
    'realtime_end': '...'} or None if no observation exists yet.
    """
    if api_key is None:
        api_key = get_secret("FRED_API_KEY")
    params: Dict[str, str] = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": obs_date,
        "observation_end": obs_date,
    }
    if realtime_start:
        params["realtime_start"] = realtime_start
    if realtime_end:
        params["realtime_end"] = realtime_end

    resp = get_with_retry(
        FRED_OBS_URL,
        params=params,
        headers={"User-Agent": "BugOutIndex/1.0 (+https://github.com/adammontville/bugoutindex)"},
    )
    obs = resp.json().get("observations") or []
    if not obs:
        return None
    o = obs[0]
    val = o.get("value")
    if val in (".", "", None):
        return None
    try:
        return {
            "value": float(val),
            "realtime_start": o.get("realtime_start"),
            "realtime_end": o.get("realtime_end"),
        }
    except ValueError:
        return None


def _initial_release_date(series_id: str, obs_date: str, api_key: str) -> Optional[str]:
    """Find when an observation was first published on FRED."""
    # Query with realtime_start=earliest possible, realtime_end=today;
    # the first row's realtime_start tells us when the value first appeared.
    resp = get_with_retry(
        FRED_OBS_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": obs_date,
            "observation_end": obs_date,
            "realtime_start": "1776-07-04",
            "realtime_end": "9999-12-31",
        },
        headers={"User-Agent": "BugOutIndex/1.0"},
    )
    rows = resp.json().get("observations") or []
    valid = [r for r in rows if r.get("value") not in (".", "", None)]
    if not valid:
        return None
    return valid[0].get("realtime_start")


# --- Vintage builders -------------------------------------------------------

def _months_back(n: int, anchor: Optional[date] = None) -> List[str]:
    """Return the first-of-month dates for the last N completed months."""
    if anchor is None:
        anchor = date.today()
    # Start from the prior month so we don't ask for the in-progress month.
    y, m = anchor.year, anchor.month
    out = []
    for i in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        out.append(date(y, m, 1).isoformat())
    return list(reversed(out))


def _add_months(iso_date: str, months: int) -> str:
    d = datetime.fromisoformat(iso_date).date()
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, min(d.day, 28)).isoformat()


def build_payems_revisions(api_key: str, today: Optional[date] = None) -> List[RevisionRow]:
    """
    Build the rolling 24-month payrolls revision table.

    For each observation month, we ask ALFRED:
        vintage_initial = value as of (initial_release_date)
        vintage_first   = value as of (initial_release_date + ~30 days)
        vintage_second  = value as of (initial_release_date + ~60 days)
    """
    rows: List[RevisionRow] = []
    today = today or date.today()
    for obs in _months_back(PAYEMS_WINDOW_MONTHS, anchor=today):
        first_pub = _initial_release_date("PAYEMS", obs, api_key)
        if first_pub is None:
            rows.append(RevisionRow(obs, None, None, None, None))
            continue

        v0 = _fetch_observation("PAYEMS", obs, first_pub, first_pub, api_key)
        v1_date = _add_months(first_pub, 1)
        v2_date = _add_months(first_pub, 2)

        # Cap revision-vintage lookups at today to avoid querying the future.
        today_iso = today.isoformat()
        v1 = _fetch_observation("PAYEMS", obs, min(v1_date, today_iso),
                                min(v1_date, today_iso), api_key) if v1_date <= today_iso else None
        v2 = _fetch_observation("PAYEMS", obs, min(v2_date, today_iso),
                                min(v2_date, today_iso), api_key) if v2_date <= today_iso else None

        rows.append(RevisionRow(
            observation_date=obs,
            vintage_initial=v0["value"] if v0 else None,
            vintage_first=v1["value"] if v1 else None,
            vintage_second=v2["value"] if v2 else None,
            initial_release_date=first_pub,
        ))
    return rows


def build_unrate_revisions(api_key: str, today: Optional[date] = None) -> dict:
    """
    Build a 5-year UNRATE comparison: value today vs value the day before
    the most recent January benchmark revision.

    The benchmark hits with the January Employment Situation release,
    typically published the first Friday of February.
    """
    today = today or date.today()
    obs_dates = _months_back(UNRATE_WINDOW_MONTHS, anchor=today)

    # Find the most recent January release (i.e., the most recent Feb release date).
    # Use Jan-1 as the observation, find its initial release date.
    jan_year = today.year if today.month >= 3 else today.year - 1
    jan_obs = date(jan_year, 1, 1).isoformat()
    benchmark_release = _initial_release_date("UNRATE", jan_obs, api_key)
    # Day before that is the "pre-benchmark" snapshot.
    pre_benchmark = (datetime.fromisoformat(benchmark_release).date()
                     - timedelta(days=1)).isoformat() if benchmark_release else None

    rows = []
    for obs in obs_dates:
        v_now = _fetch_observation("UNRATE", obs, api_key=api_key)
        v_pre = (_fetch_observation("UNRATE", obs, pre_benchmark, pre_benchmark, api_key)
                 if pre_benchmark else None)
        rows.append({
            "observation_date": obs,
            "value_current": v_now["value"] if v_now else None,
            "value_pre_benchmark": v_pre["value"] if v_pre else None,
        })

    return {
        "benchmark_release_date": benchmark_release,
        "pre_benchmark_snapshot_date": pre_benchmark,
        "rows": rows,
    }


# --- File I/O ---------------------------------------------------------------

def write_payems_csv(rows: List[RevisionRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "observation_date", "initial_release_date",
            "vintage_initial", "vintage_first", "vintage_second",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def write_unrate_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


# --- Public entrypoint ------------------------------------------------------

def fetch() -> dict:
    """
    Build both revision datasets. Called by the weekly orchestrator.

    Returns a payload suitable for embedding in latest.json plus paths
    to persisted CSV/JSON files. Failures are non-fatal: the page still
    renders with whatever cached data exists from prior runs.
    """
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set"}

    try:
        payems = build_payems_revisions(api_key)
        unrate = build_unrate_revisions(api_key)
    except RetryError as exc:
        return {"status": "error", "message": f"ALFRED unreachable: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"revision build failed: {exc}"}

    return {
        "status": "success",
        "payems": [asdict(r) for r in payems],
        "unrate": unrate,
    }


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(fetch(), indent=2, default=str))
