# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Year-over-year inflation rate from FRED's CPIAUCSL series."""
from __future__ import annotations

from runtime.util.http_retry import get_with_retry, RetryError
from runtime.util.secrets_compat import get_secret

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "CPIAUCSL"


def fetch():
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set"}

    base_params = {
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }

    try:
        # Latest CPI.
        resp = get_with_retry(FRED_API_BASE_URL, params=base_params)
        latest = resp.json()["observations"][0]
        current_cpi = float(latest["value"])
        current_date = latest["date"]

        # CPI from one year prior.
        prev_params = dict(base_params)
        prev_year_date = str(int(current_date[:4]) - 1) + current_date[4:]
        prev_params["observation_start"] = prev_year_date
        prev_params["observation_end"] = prev_year_date

        resp_prev = get_with_retry(FRED_API_BASE_URL, params=prev_params)
        previous_cpi = float(resp_prev.json()["observations"][0]["value"])

        inflation_rate = ((current_cpi - previous_cpi) / previous_cpi) * 100
        return {
            "status": "success",
            "fetched_at": current_date,
            "data": {"inflation_rate": inflation_rate},
        }
    except RetryError as exc:
        return {"status": "error", "message": f"FRED unreachable: {exc}"}
    except (KeyError, IndexError, ValueError) as exc:
        return {"status": "error", "message": f"FRED response parse error: {exc}"}
