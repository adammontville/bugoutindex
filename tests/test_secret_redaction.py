# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Credential text must not survive into stored errors or published files."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import requests

from runtime.data.fetch.fetch_food_shadow import fetch as fetch_food
from runtime.data.fetch.fetch_labor_shadow import fetch as fetch_labor
from runtime.data.fetch.fetch_revisions import fetch as fetch_revisions
from runtime.processing.formula import CORE_METRICS
from runtime.util.http_retry import RetryError
from runtime.util.redact import redact_secrets, scrub_published

ROOT = Path(__file__).resolve().parents[1]
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
PUBLISHED_DATE = "2026-09-19"

FAKE_KEY = "fk_test_fred_0123456789abcdef"
FAKE_HEADER = "hdr_test_bearer_0123456789abcdef"


def _published_raws() -> dict:
    with WEEKLY_CSV.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == PUBLISHED_DATE]
    assert len(rows) == 1
    return {metric: float(rows[0][metric]) for metric in CORE_METRICS}


def _poison() -> str:
    return (
        "GET https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=UNRATE&api_key={FAKE_KEY}&file_type=json failed; "
        f"Authorization: Bearer {FAKE_HEADER}; "
        f"X-Api-Key: {FAKE_HEADER}; "
        f"rejected {FAKE_KEY}"
    )


def test_redact_strips_url_header_and_bare_secret_and_keeps_the_rest():
    text = _poison()
    out = redact_secrets(text, secrets=[FAKE_KEY, f"Bearer {FAKE_HEADER}", FAKE_HEADER])
    assert FAKE_KEY not in out
    assert FAKE_HEADER not in out
    assert "series_id=UNRATE" in out
    assert "file_type=json" in out
    assert "api.stlouisfed.org" in out

    # Patterns alone cover the URL and header forms. A bare value needs the
    # known secret (the request param, or FRED_API_KEY in the environment).
    patterned = redact_secrets(
        "https://api.stlouisfed.org/fred?series_id=PAYEMS"
        f"&api_key={FAKE_KEY} Authorization: Bearer {FAKE_HEADER}"
    )
    assert FAKE_KEY not in patterned
    assert FAKE_HEADER not in patterned
    assert "series_id=PAYEMS" in patterned


def test_redact_leaves_the_missing_key_notice_and_ordinary_tracebacks(monkeypatch):
    notice = "FRED_API_KEY not set"
    traceback_line = 'points.sort(key=lambda row: row["date"])'
    assert redact_secrets(notice) == notice
    assert redact_secrets(traceback_line) == traceback_line
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)
    assert redact_secrets(notice) == notice
    assert FAKE_KEY not in redact_secrets(f"credential rejected: {FAKE_KEY}")


def test_fetchers_store_redacted_errors_when_the_exception_is_already_poisoned(monkeypatch):
    """Store-site scrub, even if a caller bypasses get_with_retry."""
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)

    def boom(*_args, **_kwargs):
        raise RetryError(_poison())

    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_with_retry", boom)
    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_with_retry", boom)
    monkeypatch.setattr("runtime.data.fetch.fetch_revisions.get_with_retry", boom)

    labor = fetch_labor()
    food = fetch_food()
    revisions = fetch_revisions()

    for payload in (labor, food, revisions):
        blob = json.dumps(payload)
        assert FAKE_KEY not in blob
        assert FAKE_HEADER not in blob
    assert labor["status"] == "error"
    assert labor["in_bugout_index"] is False
    assert "FRED unreachable" in labor["message"]
    assert food["status"] == "error"
    assert food["in_bugout_index"] is False
    assert revisions["status"] == "error"
    assert "ALFRED unreachable" in revisions["message"]
    assert "series_id=UNRATE" in revisions["message"]


def test_shadow_failure_publishes_without_the_key_and_keeps_the_score(tmp_path, monkeypatch, capsys):
    import runtime.publish.render as render
    import runtime.publish.weekly_run as weekly

    docs = tmp_path / "docs"
    site = tmp_path / "site"
    docs.mkdir()
    raws = _published_raws()
    previous = {
        "publication_date": "2026-09-19",
        "labor_shadow": {
            "status": "success",
            "in_bugout_index": False,
            "values": {"prime_age_epop": 80.4, "prime_age_lfpr": 83.4},
            "dates": {"prime_age_epop": "2026-08-01", "prime_age_lfpr": "2026-08-01"},
            "observations": {
                "prime_age_epop": [{"date": "2026-08-01", "value": 80.4}],
                "prime_age_lfpr": [{"date": "2026-08-01", "value": 83.4}],
            },
            "errors": [],
        },
        "food_shadow": {
            "status": "success",
            "in_bugout_index": False,
            "values": {"food_cpi_yoy": 3.1},
            "dates": {"food_cpi_yoy": "2026-08-01"},
            "observations": {"food_cpi_yoy": [{"date": "2026-08-01", "value": 3.1}]},
            "errors": [],
        },
        "revisions": {"status": "success", "payems": [], "unrate": {"rows": []}},
    }
    (docs / "latest.json").write_text(json.dumps(previous))
    monkeypatch.setattr(weekly, "DOCS_DATA", docs)
    monkeypatch.setattr(weekly, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(render, "DOCS", site)
    monkeypatch.setattr(weekly, "publication_date_for", lambda now=None: "2026-09-23")
    monkeypatch.setattr("runtime.util.http_retry.time.sleep", lambda _seconds: None)
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)
    monkeypatch.setattr(
        weekly,
        "fetch_core_metrics",
        lambda: {
            metric: {"status": "success", "data": {metric: raw}, "fetched_at": "2026-08-01"}
            for metric, raw in raws.items()
        },
    )
    monkeypatch.setattr(
        weekly,
        "fetch_markets",
        lambda: {"status": "success", "data": {"gold_usd_per_oz": 1}},
    )
    monkeypatch.setattr(weekly, "fetch_pulse", lambda: {"status": "success", "data": {}, "dates": {}})

    def fake_get(url, params=None, headers=None, timeout=None):
        key = (params or {}).get("api_key", "")
        header_text = " ".join(f"{name}: {value}" for name, value in (headers or {}).items())
        prepared = requests.Request(
            "GET",
            url,
            params=params,
            headers={"Authorization": f"Bearer {FAKE_HEADER}", **(headers or {})},
        ).prepare()
        raise requests.ConnectionError(
            "HTTPSConnectionPool(host='api.stlouisfed.org', port=443): "
            f"Max retries exceeded with url: {prepared.url} "
            f"Authorization: Bearer {FAKE_HEADER} {header_text} rejected {key}"
        )

    with patch("requests.get", side_effect=fake_get):
        assert weekly.main() == 0

    published = (docs / "latest.json").read_text()
    snapshot = json.loads(published)
    captured = capsys.readouterr()
    written = [published, captured.out, captured.err]
    for path in site.rglob("*"):
        if path.is_file():
            written.append(path.read_text(errors="replace"))
    blob = "\n".join(written)

    assert FAKE_KEY not in blob
    assert FAKE_HEADER not in blob
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["labor_shadow"]["status"] == "reused"
    assert snapshot["labor_shadow"]["in_bugout_index"] is False
    assert snapshot["labor_shadow"]["current_message"]
    assert "unreachable" in snapshot["labor_shadow"]["current_message"].lower()
    assert snapshot["food_shadow"]["status"] == "reused"
    assert snapshot["food_shadow"]["in_bugout_index"] is False
    assert snapshot["food_shadow"]["current_message"]
    assert snapshot["revisions"]["current_message"]
    assert snapshot["revisions"]["current_status"] == "error"
    assert (site / "index.html").exists()
    assert (site / "revisions.html").exists()


def test_scrub_published_walks_nested_error_strings(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)
    payload = scrub_published({
        "status": "error",
        "errors": [_poison()],
        "nested": {"current_message": f"api_key={FAKE_KEY}"},
        "score": 57.11,
    })
    blob = json.dumps(payload)
    assert FAKE_KEY not in blob
    assert FAKE_HEADER not in blob
    assert payload["score"] == 57.11
    assert payload["status"] == "error"
