# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Federal debt as a percent of GDP from FRED's GFDEGDQ188S series."""
from __future__ import annotations

from runtime.util.http_retry import get_with_retry, RetryError
from runtime.util.secrets_compat import get_secret

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "GFDEGDQ188S"


def fetch():
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set"}

    params = {
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }

    try:
        resp = get_with_retry(FRED_API_BASE_URL, params=params)
        observation = resp.json()["observations"][0]
        return {
            "status": "success",
            "fetched_at": observation["date"],
            "data": {"debt_to_gdp_ratio": float(observation["value"])},
        }
    except RetryError as exc:
        return {"status": "error", "message": f"FRED unreachable: {exc}"}
    except (KeyError, IndexError, ValueError) as exc:
        return {"status": "error", "message": f"FRED response parse error: {exc}"}
