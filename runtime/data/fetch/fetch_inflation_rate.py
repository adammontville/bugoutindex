# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Year-over-year inflation rate from FRED's CPIAUCSL series.

The rate is the percent change from the same calendar month one year
earlier:

    ((current_cpi - previous_cpi) / previous_cpi) * 100

FRED marks a month with no index as ``.`` (or an empty value). Those
months are skipped. They are not zero and they are not filled in.

The observation date is the latest month that has a real index and a
real index twelve months earlier. If that comparison month is missing,
the fetcher steps back to the newest month where both prints exist.
It does not interpolate, and it does not substitute a different month
as the year-ago index.

October 2025 (``2025-10-01``) is a missing CPIAUCSL month. An October
index therefore cannot be a year-over-year observation; the latest
usable pair is the newest earlier month that has both prints.
"""
from __future__ import annotations

from typing import Optional

from runtime.data.fetch.fred_observations import (
    CPI_OBSERVATION_LIMIT,
    parse_numeric_observations,
)
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.secrets_compat import get_secret

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "CPIAUCSL"


def prior_year_date(current_date: str) -> str:
    """Same calendar date one year earlier."""
    return str(int(current_date[:4]) - 1) + current_date[4:]


def inflation_rate_from_levels(current_cpi: float, previous_cpi: float) -> float:
    """Year-over-year percent from two CPI index levels."""
    return ((current_cpi - previous_cpi) / previous_cpi) * 100


def select_inflation(raw_observations: list) -> Optional[dict]:
    """Latest CPI month whose year-ago month is also a real print.

    ``.`` at the newest month is skipped. ``.`` in the middle of the
    series is ignored when a later pair is complete. ``.`` on the
    comparison month drops that later month and the search continues
    backward. Returns None when no complete pair is in the response.
    """
    by_date = {
        row["date"]: row["value"] for row in parse_numeric_observations(raw_observations)
    }
    for current_date in sorted(by_date, reverse=True):
        previous_date = prior_year_date(current_date)
        if previous_date not in by_date:
            continue
        current_cpi = by_date[current_date]
        previous_cpi = by_date[previous_date]
        if previous_cpi == 0:
            continue
        return {
            "observation_date": current_date,
            "comparison_date": previous_date,
            "current_cpi": current_cpi,
            "previous_cpi": previous_cpi,
            "inflation_rate": inflation_rate_from_levels(current_cpi, previous_cpi),
        }
    return None


def fetch():
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set"}

    params = {
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        # Wide enough that a trailing "." and a missing comparison month
        # still leave a complete pair inside the response.
        "limit": CPI_OBSERVATION_LIMIT,
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
        chosen = select_inflation(observations)
        if chosen is None:
            return {
                "status": "error",
                "message": (
                    "FRED response parse error: no CPI month has both a value "
                    "and a value 12 months earlier"
                ),
            }
        current_date = chosen["observation_date"]
        return {
            "status": "success",
            "fetched_at": current_date,
            # FRED observation date of the CPI month used in the rate.
            # Not the publish date, and not a month whose year-ago print
            # is missing.
            "observation_date": current_date,
            "data": {"inflation_rate": chosen["inflation_rate"]},
        }
    except RetryError as exc:
        return {"status": "error", "message": f"FRED unreachable: {exc}"}
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        return {"status": "error", "message": f"FRED response parse error: {exc}"}
