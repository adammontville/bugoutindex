# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Weekly values for gold (USD/oz), silver (USD/oz), and the broad US
Dollar Index.

Sources (all free, no key required except the FRED key we already store):
    * Gold, Silver  -> gold-api.com (spot USD/oz, updated ~hourly)
    * USD Index     -> FRED series DTWEXBGS (Nominal Broad US Dollar Index)

FRED's DTWEXBGS superseded the legacy DXY-equivalent DTWEXM in 2020; it
is the Federal Reserve's official trade-weighted broad index and is
free, daily, and does not require any third-party data redistribution.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, Optional

from runtime.util.http_retry import get_with_retry, RetryError
from runtime.util.secrets_compat import get_secret

GOLD_API_URL = "https://api.gold-api.com/price/{symbol}"
FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"
TIMEOUT = 20
UA = "Mozilla/5.0 (BugOutIndex weekly pipeline; +https://github.com/adammontville/bugoutindex)"


def _fetch_metal(symbol: str) -> Optional[dict]:
    """Fetch spot USD/oz for XAU or XAG."""
    resp = get_with_retry(
        GOLD_API_URL.format(symbol=symbol),
        headers={"User-Agent": UA, "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    body = resp.json()
    price = body.get("price")
    updated = body.get("updatedAt") or ""
    if price is None:
        return None
    return {
        "close": float(price),
        "date": updated[:10] or datetime.utcnow().strftime("%Y-%m-%d"),
    }


def _fetch_dxy_from_fred() -> Optional[dict]:
    api_key = get_secret("FRED_API_KEY")
    if not api_key:
        return None
    params = {
        "series_id": "DTWEXBGS",
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10,  # tolerate '.' placeholder rows for holidays
    }
    resp = get_with_retry(FRED_OBS_URL, params=params, timeout=TIMEOUT)
    for obs in resp.json().get("observations", []):
        if obs.get("value") not in (".", "", None):
            try:
                return {"close": float(obs["value"]), "date": obs["date"]}
            except (TypeError, ValueError):
                continue
    return None


def fetch() -> dict:
    out: Dict[str, object] = {}
    errors = []
    latest_date: Optional[str] = None

    # Gold and silver via gold-api.com.
    for key, symbol in (("gold_usd_per_oz", "XAU"), ("silver_usd_per_oz", "XAG")):
        try:
            row = _fetch_metal(symbol)
            if row is None:
                out[key] = None
                errors.append(f"{key}: no data")
                continue
            out[key] = round(row["close"], 4)
            if latest_date is None or row["date"] > latest_date:
                latest_date = row["date"]
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            out[key] = None
            errors.append(f"{key}: {exc}")

    # Broad USD index via FRED.
    try:
        row = _fetch_dxy_from_fred()
        if row is None:
            out["dxy"] = None
            errors.append("dxy: no data")
        else:
            out["dxy"] = round(row["close"], 4)
            if latest_date is None or row["date"] > latest_date:
                latest_date = row["date"]
    except Exception as exc:  # noqa: BLE001
        out["dxy"] = None
        errors.append(f"dxy: {exc}")

    filled = [v for v in out.values() if v is not None]
    status = "error" if not filled else ("partial" if errors else "success")
    return {
        "status": status,
        "fetched_at": latest_date or datetime.utcnow().strftime("%Y-%m-%d"),
        "data": out,
        "errors": errors,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
