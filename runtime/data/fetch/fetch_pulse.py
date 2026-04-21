# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Short-term 'economic pulse' indicators. These are *not* part of the core
BugOut Index calculation. They provide weekly context alongside the
slower-moving core metrics.

Series pulled from FRED:
    ICSA      - Initial Jobless Claims (weekly)
    UMCSENT   - University of Michigan Consumer Sentiment (monthly)
    NFIB      - NFIB Small Business Optimism Index (monthly)
    T10Y2Y    - 10-Year minus 2-Year Treasury spread (daily)
    VIXCLS    - CBOE Volatility Index (daily)
"""
from __future__ import annotations
from typing import Dict, Optional

import requests

from runtime.util.secrets_compat import get_secret

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
# OECD Business Confidence for the US is a free FRED substitute for NFIB
# (NFIB's Small Business Optimism Index is proprietary and not on FRED).
SERIES = {
    "initial_jobless_claims": "ICSA",
    "consumer_sentiment_umich": "UMCSENT",
    "business_confidence": "BSCICP03USM665S",
    "yield_curve_10y_2y": "T10Y2Y",
    "vix": "VIXCLS",
}
TIMEOUT = 20


def _latest(series_id: str, api_key: str) -> Optional[dict]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,  # get a few in case the newest is '.'
    }
    resp = requests.get(FRED_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])
    for o in obs:
        if o.get("value") not in (".", "", None):
            try:
                return {"date": o["date"], "value": float(o["value"])}
            except (TypeError, ValueError):
                continue
    return None


def fetch() -> dict:
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "message": "FRED_API_KEY not set", "data": {}}

    out: Dict[str, object] = {}
    dates: Dict[str, str] = {}
    errors = []
    for name, sid in SERIES.items():
        try:
            row = _latest(sid, api_key)
            if row is None:
                out[name] = None
                errors.append(f"{name}: no observations")
                continue
            out[name] = row["value"]
            dates[name] = row["date"]
        except Exception as exc:  # noqa: BLE001
            out[name] = None
            errors.append(f"{name}: {exc}")

    status = "success" if not errors else ("partial" if any(v is not None for v in out.values()) else "error")
    return {
        "status": status,
        "fetched_at": max(dates.values()) if dates else "",
        "data": out,
        "dates": dates,
        "errors": errors,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
