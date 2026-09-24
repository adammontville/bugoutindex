# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Headless weekly runner.

Responsibilities:
    1. Shim `streamlit.secrets` so existing fetchers work without a
       Streamlit runtime (reading FRED_API_KEY from env vars instead).
    2. Fetch all six core BOI metrics and compute the weighted index.
    3. Fetch metals (gold, silver, DXY), the short-term economic pulse,
       the labor-utilization shadow series, and the food-price shadow
       series (not index inputs; a shadow failure does not refuse the publish).
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
from runtime.util.redact import redact_secrets, scrub_published  # noqa: E402
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
            message = redact_secrets(str(exc))
            print(f"[error] fetch {metric}: {message}", file=sys.stderr)
            out[metric] = {"status": "error", "message": message, "data": {}}
    return out


def fetch_markets() -> Dict[str, Any]:
    mod = importlib.import_module("data.fetch.fetch_markets")
    return mod.fetch()


def fetch_pulse() -> Dict[str, Any]:
    # Use absolute import so get_secret works regardless of CWD.
    sys.path.insert(0, str(REPO_ROOT))
    mod = importlib.import_module("runtime.data.fetch.fetch_pulse")
    return mod.fetch()


def _shadow_fetch_error(label: str, exc: Exception) -> Dict[str, Any]:
    message = redact_secrets(f"{label} fetch raised: {exc}")
    return {
        "status": "error",
        "in_bugout_index": False,
        "message": message,
        "series_ids": {},
        "values": {},
        "dates": {},
        "observations": {},
        "errors": [message],
    }


def fetch_labor_shadow() -> Dict[str, Any]:
    """Prime-age EPOP and participation. Not an index input.

    A raised exception becomes ``status: error`` so the publish can continue.
    """
    sys.path.insert(0, str(REPO_ROOT))
    try:
        mod = importlib.import_module("runtime.data.fetch.fetch_labor_shadow")
        return mod.fetch()
    except Exception as exc:  # noqa: BLE001
        return _shadow_fetch_error("labor shadow", exc)


def fetch_food_shadow() -> Dict[str, Any]:
    """Food CPI, 12-month percent change. Not an index input.

    A raised exception becomes ``status: error`` so the publish can continue.
    """
    sys.path.insert(0, str(REPO_ROOT))
    try:
        mod = importlib.import_module("runtime.data.fetch.fetch_food_shadow")
        return mod.fetch()
    except Exception as exc:  # noqa: BLE001
        return _shadow_fetch_error("food shadow", exc)


def _shadow_has_value(block: Dict[str, Any]) -> bool:
    values = block.get("values") or {}
    return any(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values.values())


def _labor_has_value(block: Dict[str, Any]) -> bool:
    return _shadow_has_value(block)


def _read_previous_snapshot() -> Dict[str, Any]:
    path = DOCS_DATA / "latest.json"
    try:
        if path.exists():
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict):
                return loaded
    except Exception as exc:  # noqa: BLE001
        print(f"[weekly_run] could not read prior snapshot: {exc}", file=sys.stderr)
    return {}


def _resolve_shadow(payload: Dict[str, Any], block_key: str) -> Dict[str, Any]:
    """Keep a failed shadow fetch from blanking a series we already published.

    Carried-forward observation dates stay the FRED dates on the previous
    block. Nothing here writes the current clock.
    """
    block = dict(payload or {})
    block["in_bugout_index"] = False
    if block.get("status") in ("success", "partial") and _shadow_has_value(block):
        return block
    previous = _read_previous_snapshot()
    prior = previous.get(block_key) or {}
    if isinstance(prior, dict) and _shadow_has_value(prior):
        carried = dict(prior)
        carried["in_bugout_index"] = False
        carried["status"] = "reused"
        carried["reused_from"] = previous.get("publication_date")
        carried["current_status"] = block.get("status")
        message = block.get("message") or "; ".join(block.get("errors") or [])
        if message:
            carried["current_message"] = message
        return carried
    return block


def _resolve_labor_shadow(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _resolve_shadow(payload, "labor_shadow")


def _resolve_food_shadow(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _resolve_shadow(payload, "food_shadow")


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
        return {"status": "error", "message": redact_secrets(f"revisions fetch raised: {exc}")}


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


def _append_shadow_row(csv_name: str, module_name: str, run_date: str, shadow: Dict[str, Any]) -> None:
    """One weekly row. Observation-date cells are FRED dates or blank."""
    mod = importlib.import_module(module_name)
    keys = list(mod.SERIES)
    values = shadow.get("values") or {}
    dates = shadow.get("dates") or {}
    if not any(isinstance(values.get(key), (int, float)) and not isinstance(values.get(key), bool) for key in keys):
        return
    headers = ["date"]
    row: Dict[str, Any] = {"date": run_date}
    for key in keys:
        headers.append(key)
        headers.append(f"{key}_observation_date")
        value = values.get(key)
        row[key] = "" if value is None else value
        row[f"{key}_observation_date"] = dates.get(key) or ""
    _append_row(DATA_DIR / csv_name, headers, row)


def _append_labor_shadow(run_date: str, labor_shadow: Dict[str, Any]) -> None:
    _append_shadow_row(
        "labor_shadow_history.csv",
        "runtime.data.fetch.fetch_labor_shadow",
        run_date,
        labor_shadow,
    )


def _append_food_shadow(run_date: str, food_shadow: Dict[str, Any]) -> None:
    _append_shadow_row(
        "food_shadow_history.csv",
        "runtime.data.fetch.fetch_food_shadow",
        run_date,
        food_shadow,
    )


def append_history(run_date: str, boi: Dict[str, Any],
                   markets: Dict[str, Any], pulse: Dict[str, Any],
                   core: Dict[str, Dict[str, Any]] | None = None,
                   labor_shadow: Dict[str, Any] | None = None,
                   food_shadow: Dict[str, Any] | None = None) -> None:
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

    if labor_shadow is not None:
        _append_labor_shadow(run_date, labor_shadow)
    if food_shadow is not None:
        _append_food_shadow(run_date, food_shadow)


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
    # Candidate crime rates live here. compute_index reads only data[metric].
    diagnostics = payload.get("diagnostics")
    if diagnostics:
        block["diagnostics"] = diagnostics
    return block


def build_snapshot(run_date: str, boi: Dict[str, Any],
                   core: Dict[str, Dict[str, Any]],
                   markets: Dict[str, Any],
                   pulse: Dict[str, Any],
                   labor_shadow: Dict[str, Any] | None = None,
                   food_shadow: Dict[str, Any] | None = None) -> Dict[str, Any]:
    band = interpret(boi["index"])
    snapshot = {
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
    if labor_shadow is not None:
        block = dict(labor_shadow)
        block["in_bugout_index"] = False
        snapshot["labor_shadow"] = block
    if food_shadow is not None:
        block = dict(food_shadow)
        block["in_bugout_index"] = False
        snapshot["food_shadow"] = block
    return snapshot


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

    # Hard-fail if markets or the pulse returned no usable data at all.
    # Labor and food shadows are companions: their failure must not refuse the publish.
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

    print("[weekly_run] fetching labor utilization shadow (not in the index)…")
    labor_shadow = fetch_labor_shadow()
    if labor_shadow.get("status") not in ("success", "partial"):
        print(
            "[weekly_run] labor shadow failed (publishing anyway): "
            f"{labor_shadow.get('message') or labor_shadow.get('errors')}",
            file=sys.stderr,
        )
    elif labor_shadow.get("errors"):
        print(
            f"[weekly_run] labor shadow partial (publishing anyway): {labor_shadow['errors']}",
            file=sys.stderr,
        )
    labor_shadow = _resolve_labor_shadow(labor_shadow)

    print("[weekly_run] fetching food-price shadow (not in the index)…")
    food_shadow = fetch_food_shadow()
    if food_shadow.get("status") not in ("success", "partial"):
        print(
            "[weekly_run] food shadow failed (publishing anyway): "
            f"{food_shadow.get('message') or food_shadow.get('errors')}",
            file=sys.stderr,
        )
    elif food_shadow.get("errors"):
        print(
            f"[weekly_run] food shadow partial (publishing anyway): {food_shadow['errors']}",
            file=sys.stderr,
        )
    food_shadow = _resolve_food_shadow(food_shadow)

    # Soft-warn if any partial failures occurred (some pulse items missing, etc.).
    partial_warnings = _summarize_failures(core, markets, pulse)
    if partial_warnings:
        print("[weekly_run] partial failures (publishing anyway):", file=sys.stderr)
        for line in partial_warnings:
            print(f"  - {line}", file=sys.stderr)

    print("[weekly_run] appending history…")
    append_history(run_date, boi, markets, pulse, core, labor_shadow, food_shadow)

    snapshot = build_snapshot(run_date, boi, core, markets, pulse, labor_shadow, food_shadow)

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
        "labor_shadow": load_history(DATA_DIR / "labor_shadow_history.csv"),
        "food_shadow": load_history(DATA_DIR / "food_shadow_history.csv"),
    }

    # Shadow and revision failures are published on exit 0. Scrub the
    # snapshot that both latest.json and the HTML are built from.
    snapshot = scrub_published(snapshot)
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    published = redact_secrets(json.dumps(snapshot, indent=2, default=str))
    (DOCS_DATA / "latest.json").write_text(published)
    print(f"[weekly_run] wrote {DOCS_DATA / 'latest.json'}")

    # Also render the static site from the same scrubbed payload.
    from runtime.publish.render import render_site  # lazy import
    render_site(json.loads(published))
    print("[weekly_run] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
