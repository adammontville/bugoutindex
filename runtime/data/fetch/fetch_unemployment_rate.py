# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Civilian unemployment rate from FRED's UNRATE series.

FRED's ``.`` and empty observations are missing. They are skipped. The
value and the observation date are the latest real print. A missing
month is not carried forward into a later month and is not interpolated.
"""
from __future__ import annotations

from runtime.data.fetch.fred_observations import (
    LEVEL_OBSERVATION_LIMIT,
    parse_numeric_observations,
)
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.secrets_compat import get_secret

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "UNRATE"


def fetch():
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set"}

    params = {
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": LEVEL_OBSERVATION_LIMIT,
    }

    try:
        resp = get_with_retry(FRED_API_BASE_URL, params=params)
        body = resp.json()
        observations = body["observations"] if isinstance(body, dict) else None
        if not isinstance(observations, list):
            return {
                "status": "error",
                "message": "FRED response parse error: missing observations",
            }
        points = parse_numeric_observations(observations)
        if not points:
            return {
                "status": "error",
                "message": "FRED response parse error: no numeric observations",
            }
        observation = points[-1]
        return {
            "status": "success",
            "fetched_at": observation["date"],
            # FRED observation date (month), kept separate from the publish date.
            "observation_date": observation["date"],
            "data": {"unemployment_rate": observation["value"]},
        }
    except RetryError as exc:
        return {"status": "error", "message": f"FRED unreachable: {exc}"}
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        return {"status": "error", "message": f"FRED response parse error: {exc}"}
