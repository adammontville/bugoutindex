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
from zoneinfo import ZoneInfo

# Repo paths — this file lives at runtime/publish/weekly_run.py
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "runtime"
DATA_DIR = RUNTIME_DIR / "data"
DOCS_DATA = REPO_ROOT / "docs" / "data"

# Editorial week is the U.S. Central calendar date, not the UTC date.
# A Friday cron that GitHub starts just after 00:00 UTC Saturday is still Friday here.
PUBLICATION_TZ = ZoneInfo("America/Chicago")

# Make `data.fetch.fetch_<metric>` importable (the existing modules use that path).
sys.path.insert(0, str(RUNTIME_DIR))
# Repo root so `runtime.processing.formula` imports when this file is executed directly.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# v1.0.0 formula: endpoints, weights, inversion, clamp, aggregation, bands.
# Rebound here so existing callers of weekly_run keep the same entry points.
import runtime.processing.formula as _formula  # noqa: E402
from runtime.publish.failure_notice import (  # noqa: E402
    EXIT_CORE_REFUSED,
    EXIT_MARKETS_OR_PULSE_REFUSED,
)
from runtime.publish.observation_dates import (  # noqa: E402
    blank_observation_dates,
    ensure_csv_schema,
    observation_column,
    observation_date_for,
    weekly_boi_headers,
)

CORE_METRICS = _formula.CORE_METRICS
METRIC_RANGES = _formula.METRIC_RANGES
WEIGHTS = _formula.WEIGHTS
normalize = _formula.normalize
compute_index = _formula.compute_index
interpret = _formula.interpret


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


def fetch_markets() -> Dict[str, Any]:
    mod = importlib.import_module("data.fetch.fetch_markets")
    return mod.fetch()


def fetch_pulse() -> Dict[str, Any]:
    # Use absolute import so get_secret works regardless of CWD.
    sys.path.insert(0, str(REPO_ROOT))
    mod = importlib.import_module("runtime.data.fetch.fetch_pulse")
    return mod.fetch()


def fetch_revisions() -> Dict[str, Any]:
    """
    Pull PAYEMS + UNRATE revision history from ALFRED.

    Non-fatal: if this fails the rest of the run continues; the revisions
    page will reuse the last successful payload from the previous snapshot.
    """
    sys.path.insert(0, str(REPO_ROOT))
    try:
        mod = importlib.import_module("runtime.data.fetch.fetch_revisions")
        return mod.fetch()
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"revisions fetch raised: {exc}"}


def _append_row(csv_path: Path, headers: list, row: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    exists = csv_path.exists()
    with csv_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)


def core_history_row(run_date: str, boi: Dict[str, Any],
                     core: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """One weekly index row: raw value, observation date, then normalized score.

    Missing observation dates are blank. They are not guessed.
    """
    row: Dict[str, Any] = {"date": run_date, "bugout_index": boi["index"]}
    for metric in CORE_METRICS:
        row[metric] = boi["metrics"][metric]["raw"]
        observed = observation_date_for(metric, core.get(metric) or {})
        row[observation_column(metric)] = observed or ""
        row[f"{metric}_normalized"] = boi["metrics"][metric]["normalized"]
    return row


def append_history(run_date: str, boi: Dict[str, Any],
                   markets: Dict[str, Any], pulse: Dict[str, Any],
                   core: Dict[str, Dict[str, Any]] | None = None) -> None:
    # Flat core metrics history (replaces the old dict-stringified CSV going forward).
    boi_path = DATA_DIR / "weekly_bugout_index.csv"
    # Old files gain the observation-date columns with blank cells. Dates are
    # not backfilled here; see observation_dates.apply_known_dates.
    ensure_csv_schema(boi_path)
    boi_headers = weekly_boi_headers()
    boi_row = core_history_row(run_date, boi, core or {})
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


def _metric_snapshot(metric: str, scored: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Copy the scored inputs plus dating metadata. Provenance is not an input."""
    block: Dict[str, Any] = {
        **scored,
        "observation_date": observation_date_for(metric, payload),
        "source_fetched_at": payload.get("fetched_at"),
        "status": payload.get("status"),
    }
    provenance = payload.get("provenance")
    if provenance:
        block["provenance"] = provenance
    return block


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
            m: _metric_snapshot(m, boi["metrics"][m], core.get(m, {}))
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


def publication_date_for(now: datetime | None = None) -> str:
    """Calendar date for this publish, in America/Chicago.

    ``now`` should be timezone-aware. A naive value is read as UTC, which is
    the clock GitHub Actions uses. The result is ``YYYY-MM-DD``.

    This applies to new runs only. Rows already stored in the history CSVs
    are not rewritten.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(PUBLICATION_TZ).strftime("%Y-%m-%d")


def load_history(path: Path, limit: int = 52) -> list:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    rows = blank_observation_dates(rows)
    return rows[-limit:]


MIN_REQUIRED_METRICS = 6  # all six must succeed; refuse to publish a degraded BOI


def _summarize_failures(core, markets, pulse) -> list:
    failed = []
    for metric, payload in core.items():
        if payload.get("status") != "success":
            failed.append(f"core.{metric}: {payload.get('message') or payload.get('errors')}")
    if markets.get("status") not in ("success", "partial"):
        failed.append(f"markets: {markets.get('errors') or markets.get('message')}")
    elif markets.get("errors"):
        failed.append(f"markets (partial): {markets['errors']}")
    if pulse.get("status") not in ("success", "partial"):
        failed.append(f"pulse: {pulse.get('errors') or pulse.get('message')}")
    elif pulse.get("errors"):
        failed.append(f"pulse (partial): {pulse['errors']}")
    return failed


def main() -> int:
    run_date = publication_date_for()

    print(f"[weekly_run] {run_date} — fetching core metrics…")
    core = fetch_core_metrics()
    boi = compute_index(core)
    print(f"[weekly_run] BOI = {boi['index']}")

    successful_core = sum(1 for m in CORE_METRICS
                          if core.get(m, {}).get("status") == "success")
    if successful_core < MIN_REQUIRED_METRICS:
        missing = [m for m in CORE_METRICS
                   if core.get(m, {}).get("status") != "success"]
        msg = (f"REFUSING TO PUBLISH: only {successful_core}/{MIN_REQUIRED_METRICS} "
               f"core metrics succeeded. Missing: {missing}")
        for line in _summarize_failures(core, {}, {}):
            print(f"  - {line}", file=sys.stderr)
        print(msg, file=sys.stderr)
        return EXIT_CORE_REFUSED

    print("[weekly_run] fetching markets…")
    markets = fetch_markets()

    print("[weekly_run] fetching short-term pulse…")
    pulse = fetch_pulse()

    print("[weekly_run] fetching revision history (PAYEMS, UNRATE)…")
    revisions = fetch_revisions()
    if revisions.get("status") != "success":
        print(f"[weekly_run] revisions: {revisions.get('message') or revisions.get('status')}",
              file=sys.stderr)

    # Hard-fail if any non-core fetcher returned no usable data at all.
    hard_failures = []
    if markets.get("status") == "error":
        hard_failures.append("markets fully failed")
    if pulse.get("status") == "error":
        hard_failures.append("pulse fully failed")
    if hard_failures:
        for line in _summarize_failures(core, markets, pulse):
            print(f"  - {line}", file=sys.stderr)
        print(f"REFUSING TO PUBLISH: {'; '.join(hard_failures)}", file=sys.stderr)
        return EXIT_MARKETS_OR_PULSE_REFUSED

    # Soft-warn if any partial failures occurred (some pulse items missing, etc.).
    partial_warnings = _summarize_failures(core, markets, pulse)
    if partial_warnings:
        print("[weekly_run] partial failures (publishing anyway):", file=sys.stderr)
        for line in partial_warnings:
            print(f"  - {line}", file=sys.stderr)

    print("[weekly_run] appending history…")
    append_history(run_date, boi, markets, pulse, core)

    snapshot = build_snapshot(run_date, boi, core, markets, pulse)

    # Carry the previous revisions payload forward if this week's fetch failed.
    if revisions.get("status") == "success":
        snapshot["revisions"] = revisions
    else:
        prev_path = DOCS_DATA / "latest.json"
        try:
            if prev_path.exists():
                prev = json.loads(prev_path.read_text())
                if prev.get("revisions", {}).get("status") == "success":
                    snapshot["revisions"] = {
                        **prev["revisions"],
                        "reused_from": prev.get("publication_date"),
                        "current_status": revisions.get("status"),
                        "current_message": revisions.get("message"),
                    }
                else:
                    snapshot["revisions"] = revisions
            else:
                snapshot["revisions"] = revisions
        except Exception as exc:  # noqa: BLE001
            print(f"[weekly_run] could not reuse prior revisions: {exc}", file=sys.stderr)
            snapshot["revisions"] = revisions

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
