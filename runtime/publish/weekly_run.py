# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Headless weekly runner.

Responsibilities:
    1. Shim `streamlit.secrets` so existing fetchers work without a
       Streamlit runtime (reading FRED_API_KEY from env vars instead).
    2. Fetch all six core BOI metrics and compute the weighted index.
    3. Fetch metals (gold, silver, DXY) and the short-term economic pulse.
    4. Append a flat row to the weekly history CSVs.
    5. Emit a single `docs/data/latest.json` snapshot consumed by the
       static-site renderer.
"""
from __future__ import annotations

# ---------- Streamlit secrets shim (must run BEFORE fetcher imports) ----------
import os
import sys
import types


class _SecretsDict(dict):
    def __getitem__(self, key):  # type: ignore[override]
        val = os.environ.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


try:
    import streamlit  # noqa: F401
    streamlit.secrets = _SecretsDict()  # type: ignore[attr-defined]
except ImportError:
    fake = types.ModuleType("streamlit")
    fake.secrets = _SecretsDict()  # type: ignore[attr-defined]
    sys.modules["streamlit"] = fake
# ------------------------------------------------------------------------------

import csv
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Repo paths — this file lives at runtime/publish/weekly_run.py
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "runtime"
DATA_DIR = RUNTIME_DIR / "data"
DOCS_DATA = REPO_ROOT / "docs" / "data"

# Make `data.fetch.fetch_<metric>` importable (the existing modules use that path).
sys.path.insert(0, str(RUNTIME_DIR))

# Core metrics — must match the v1.0.0 methodology.
CORE_METRICS = [
    "inflation_rate",
    "incident_rate",           # crime rate (per 100k)
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
]

METRIC_RANGES: Dict[str, tuple] = {
    "inflation_rate": (-10, 15),
    "incident_rate": (500, 8000),
    "unemployment_rate": (0, 25),
    "debt_to_gdp_ratio": (0, 200),
    "homelessness_rate": (0, 0.5),
    "trust_in_government": (0, 80),  # trust is inverted (higher = better)
}

WEIGHTS: Dict[str, float] = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_to_gdp_ratio": 0.12,
    "homelessness_rate": 0.09,
    "trust_in_government": 0.12,
}


def normalize(raw: float, lo: float, hi: float, inverse: bool = False) -> float:
    """Normalize to 0-100. Higher = more stable."""
    if hi == lo:
        return 0.0
    score = (1 - ((raw - lo) / (hi - lo))) * 100
    if inverse:
        score = 100 - score
    return max(0.0, min(100.0, score))


def fetch_core_metrics() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for metric in CORE_METRICS:
        try:
            mod = importlib.import_module(f"data.fetch.fetch_{metric}")
            result = mod.fetch()
            if result.get("status") != "success":
                print(f"[warn] {metric}: {result}", file=sys.stderr)
            out[metric] = result
        except Exception as exc:  # noqa: BLE001
            print(f"[error] fetch {metric}: {exc}", file=sys.stderr)
            out[metric] = {"status": "error", "message": str(exc), "data": {}}
    return out


def compute_index(metric_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    total_weighted = 0.0
    total_weight = 0.0
    per_metric = {}
    for metric in CORE_METRICS:
        payload = metric_results.get(metric, {})
        data = payload.get("data") or {}
        raw = data.get(metric)
        if raw is None or not isinstance(raw, (int, float)):
            per_metric[metric] = {"raw": None, "normalized": None, "weight": WEIGHTS[metric]}
            continue
        lo, hi = METRIC_RANGES[metric]
        norm = normalize(float(raw), lo, hi, inverse=(metric == "trust_in_government"))
        per_metric[metric] = {
            "raw": float(raw),
            "normalized": round(norm, 2),
            "weight": WEIGHTS[metric],
        }
        total_weighted += norm * WEIGHTS[metric]
        total_weight += WEIGHTS[metric]

    index = round(total_weighted / total_weight, 2) if total_weight else 0.0
    return {"index": index, "metrics": per_metric}


def interpret(index: float) -> Dict[str, str]:
    if index >= 70:
        return {"band": "High Stability", "risk": "Low Risk", "band_key": "high"}
    if index >= 55:
        return {"band": "Moderate Stability", "risk": "Warning Signs", "band_key": "moderate"}
    if index >= 40:
        return {"band": "Low Stability", "risk": "Heightened Risk", "band_key": "low"}
    return {"band": "Critical Instability", "risk": "Collapse Likely", "band_key": "critical"}


def fetch_markets() -> Dict[str, Any]:
    mod = importlib.import_module("data.fetch.fetch_markets")
    return mod.fetch()


def fetch_pulse() -> Dict[str, Any]:
    # Use absolute import so get_secret works regardless of CWD.
    sys.path.insert(0, str(REPO_ROOT))
    mod = importlib.import_module("runtime.data.fetch.fetch_pulse")
    return mod.fetch()


def _append_row(csv_path: Path, headers: list, row: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    exists = csv_path.exists()
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)


def append_history(run_date: str, boi: Dict[str, Any],
                   markets: Dict[str, Any], pulse: Dict[str, Any]) -> None:
    # Flat core metrics history (replaces the old dict-stringified CSV going forward).
    boi_path = DATA_DIR / "weekly_bugout_index.csv"
    boi_headers = ["date", "bugout_index"] + CORE_METRICS + [f"{m}_normalized" for m in CORE_METRICS]
    boi_row: Dict[str, Any] = {"date": run_date, "bugout_index": boi["index"]}
    for m in CORE_METRICS:
        boi_row[m] = boi["metrics"][m]["raw"]
        boi_row[f"{m}_normalized"] = boi["metrics"][m]["normalized"]
    _append_row(boi_path, boi_headers, boi_row)

    # Markets history.
    m_data = markets.get("data", {}) or {}
    _append_row(
        DATA_DIR / "markets_history.csv",
        ["date", "gold_usd_per_oz", "silver_usd_per_oz", "dxy"],
        {"date": run_date, **{k: m_data.get(k) for k in ("gold_usd_per_oz", "silver_usd_per_oz", "dxy")}},
    )

    # Pulse history.
    p_data = pulse.get("data", {}) or {}
    p_headers = ["date",
                 "initial_jobless_claims",
                 "consumer_sentiment_umich",
                 "business_confidence",
                 "yield_curve_10y_2y",
                 "vix"]
    _append_row(DATA_DIR / "pulse_history.csv", p_headers, {"date": run_date, **p_data})


def build_snapshot(run_date: str, boi: Dict[str, Any],
                   core: Dict[str, Dict[str, Any]],
                   markets: Dict[str, Any],
                   pulse: Dict[str, Any]) -> Dict[str, Any]:
    band = interpret(boi["index"])
    return {
        "schema_version": 1,
        "methodology_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "publication_date": run_date,
        "bugout_index": boi["index"],
        "interpretation": band,
        "metrics": {
            m: {
                **boi["metrics"][m],
                "source_fetched_at": core.get(m, {}).get("fetched_at"),
                "status": core.get(m, {}).get("status"),
            }
            for m in CORE_METRICS
        },
        "markets": {
            "status": markets.get("status"),
            "fetched_at": markets.get("fetched_at"),
            **(markets.get("data") or {}),
        },
        "pulse": {
            "status": pulse.get("status"),
            "fetched_at": pulse.get("fetched_at"),
            "values": pulse.get("data", {}),
            "dates": pulse.get("dates", {}),
        },
    }


def load_history(path: Path, limit: int = 52) -> list:
    if not path.exists():
        return []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def main() -> int:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[weekly_run] {run_date} — fetching core metrics…")
    core = fetch_core_metrics()
    boi = compute_index(core)
    print(f"[weekly_run] BOI = {boi['index']}")

    print("[weekly_run] fetching markets…")
    markets = fetch_markets()

    print("[weekly_run] fetching short-term pulse…")
    pulse = fetch_pulse()

    print("[weekly_run] appending history…")
    append_history(run_date, boi, markets, pulse)

    snapshot = build_snapshot(run_date, boi, core, markets, pulse)
    snapshot["history"] = {
        "bugout_index": load_history(DATA_DIR / "weekly_bugout_index.csv"),
        "markets": load_history(DATA_DIR / "markets_history.csv"),
        "pulse": load_history(DATA_DIR / "pulse_history.csv"),
    }

    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / "latest.json").write_text(json.dumps(snapshot, indent=2, default=str))
    print(f"[weekly_run] wrote {DOCS_DATA / 'latest.json'}")

    # Also render the static site.
    from runtime.publish.render import render_site  # lazy import
    render_site(snapshot)
    print("[weekly_run] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
