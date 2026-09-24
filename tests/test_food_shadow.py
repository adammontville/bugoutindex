# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Food CPI year-over-year stays outside compute_index."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_food_shadow import (
    SERIES,
    _public_yoy,
    assemble,
    fetch,
    parse_index,
    year_over_year,
)
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index
from runtime.publish.failure_notice import EXIT_MARKETS_OR_PULSE_REFUSED
from runtime.publish.render import FOOD_SHADOW_LABELS, render_site
from runtime.publish.week_note import build_week_note, unexplained_numerals
from runtime.publish.weekly_run import build_snapshot
from runtime.util.http_retry import RetryError

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
PUBLISHED_DATE = "2026-09-19"
LOCKED_CORE = {
    "inflation_rate",
    "incident_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
}


def _published_raws() -> dict:
    with WEEKLY_CSV.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == PUBLISHED_DATE]
    assert len(rows) == 1
    return {metric: float(rows[0][metric]) for metric in CORE_METRICS}


def _payload(raws: dict) -> dict:
    return {metric: {"status": "success", "data": {metric: value}} for metric, value in raws.items()}


def test_shadow_series_is_absent_from_compute_index_and_locked_score_holds():
    raws = _published_raws()
    assert set(CORE_METRICS) == LOCKED_CORE
    assert "food_cpi_yoy" not in CORE_METRICS
    assert "food_cpi_yoy" not in WEIGHTS
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text()
    assert "CPIUFDNS" not in formula
    assert "food_cpi_yoy" not in formula

    plain = compute_index(_payload(raws))
    assert plain["index"] == 57.11
    assert plain["metrics"]["incident_rate"]["raw"] == 2723.0

    stuffed = _payload(raws)
    stuffed["food_cpi_yoy"] = {"data": {"food_cpi_yoy": 9.9}}
    stuffed["food_shadow"] = {"data": {"food_cpi_yoy": 9.9}}
    scored = compute_index(stuffed)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert "food_cpi_yoy" not in scored["metrics"]
    assert list(scored["metrics"]) == list(CORE_METRICS)


def test_series_id_is_the_verified_fred_nsa_food_index():
    assert SERIES == {"food_cpi_yoy": "CPIUFDNS"}
    assert list(SERIES) == list(FOOD_SHADOW_LABELS)
    assert FOOD_SHADOW_LABELS["food_cpi_yoy"][2] == "CPIUFDNS"


def test_august_2026_matches_the_bls_12_month_print():
    # FRED CPIUFDNS index levels. BLS CUUR0000SAF1 12-month table:
    # August 2026 is 2.7, July 2026 is 3.0.
    assert _public_yoy("350.418", "341.295") == 2.7
    assert _public_yoy("350.164", "340.036") == 3.0
    # Half-up, not banker's rounding: 2.25% prints as 2.3.
    assert _public_yoy("1022.5", "1000") == 2.3


def test_parse_keeps_fred_dates_and_drops_placeholders():
    rows = parse_index([
        {"date": "2026-08-01", "value": "350.418"},
        {"date": "2025-10-01", "value": "."},
        {"date": "2025-08-01", "value": "341.295"},
        {"observation_date": "not-a-date", "value": "1"},
    ])
    assert rows == [
        {"date": "2025-08-01", "value": "341.295"},
        {"date": "2026-08-01", "value": "350.418"},
    ]


def test_year_over_year_uses_the_later_fred_date_and_skips_gaps():
    rows = year_over_year([
        {"date": "2024-08-01", "value": "330.750"},
        {"date": "2024-10-01", "value": "332.678"},
        {"date": "2025-08-01", "value": "341.295"},
        {"date": "2026-08-01", "value": "350.418"},
    ])
    assert rows[0] == {"date": "2025-08-01", "value": _public_yoy("341.295", "330.750")}
    assert rows[-1] == {"date": "2026-08-01", "value": 2.7}
    assert all(row["date"] != "2026-10-01" for row in rows)
    assert "2025-10-01" not in [row["date"] for row in rows]


def test_missing_api_key_does_not_invent_a_timestamp(monkeypatch):
    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_secret", lambda _key: None)
    payload = fetch()
    assert payload["status"] == "error"
    assert payload["in_bugout_index"] is False
    assert payload["dates"] == {}
    assert payload["values"]["food_cpi_yoy"] is None
    blob = json.dumps(payload)
    assert "T" not in blob
    assert "2026-" not in blob


def test_fetch_stores_fred_observation_dates(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        assert params["series_id"] == "CPIUFDNS"
        assert "units" not in params

        class Response:
            def json(self):
                return {"observations": [
                    {"date": "2026-08-01", "value": "350.418"},
                    {"date": "2025-10-01", "value": "."},
                    {"date": "2025-08-01", "value": "341.295"},
                    {"date": "2024-08-01", "value": "330.750"},
                ]}

        return Response()

    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_with_retry", fake_get)
    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_secret", lambda _key: "test-key")
    payload = fetch()
    assert payload["status"] == "success"
    assert payload["in_bugout_index"] is False
    assert payload["series_ids"] == {"food_cpi_yoy": "CPIUFDNS"}
    assert payload["bls_series_ids"] == {"food_cpi_yoy": "CUUR0000SAF1"}
    assert payload["reading"] == "12-month percent change"
    assert payload["seasonal_adjustment"] == "not seasonally adjusted"
    assert payload["dates"] == {"food_cpi_yoy": "2026-08-01"}
    assert payload["values"]["food_cpi_yoy"] == 2.7
    assert payload["observations"]["food_cpi_yoy"][-1] == {"date": "2026-08-01", "value": 2.7}
    assert "fetched_at" not in payload
    assert "T" not in json.dumps(payload["dates"])


def test_fred_failure_is_an_error_and_does_not_invent_a_date(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        raise RetryError("down")

    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_with_retry", fake_get)
    monkeypatch.setattr("runtime.data.fetch.fetch_food_shadow.get_secret", lambda _key: "test-key")
    payload = fetch()
    assert payload["status"] == "error"
    assert payload["values"]["food_cpi_yoy"] is None
    assert payload["dates"] == {}
    assert payload["in_bugout_index"] is False


def test_snapshot_records_the_shadow_series_without_changing_the_index():
    raws = _published_raws()
    scored = compute_index(_payload(raws))
    food = assemble(
        {"food_cpi_yoy": [{"date": "2026-08-01", "value": 2.7}]},
        [],
    )
    food["in_bugout_index"] = True  # the publisher must force this back off
    snapshot = build_snapshot(
        PUBLISHED_DATE,
        scored,
        _payload(raws),
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
        None,
        food,
    )
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["food_shadow"]["in_bugout_index"] is False
    assert snapshot["food_shadow"]["dates"]["food_cpi_yoy"] == "2026-08-01"
    assert "food_cpi_yoy" not in snapshot["metrics"]


def test_week_note_mentions_the_shadow_series_only_as_companion_context():
    snapshot = json.loads(LATEST.read_text())
    snapshot["food_shadow"] = {
        "in_bugout_index": False,
        "values": {"food_cpi_yoy": 2.7},
        "dates": {"food_cpi_yoy": "2026-08-01"},
    }
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == []
    assert "food-price shadow series" in note[-1]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "2.7" not in text
    assert "CPIUFDNS" not in text


def test_rendered_page_labels_the_shadow_series_outside_the_index(tmp_path, monkeypatch):
    import runtime.publish.render as render

    snapshot = json.loads(LATEST.read_text())
    snapshot["food_shadow"] = assemble(
        {
            "food_cpi_yoy": [
                {"date": "2026-07-01", "value": 3.0},
                {"date": "2026-08-01", "value": 2.7},
            ],
        },
        [],
    )
    snapshot.setdefault("history", {})["food_shadow"] = [{
        "date": snapshot["publication_date"],
        "food_cpi_yoy": "2.7",
        "food_cpi_yoy_observation_date": "2026-08-01",
    }]
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)
    html = (tmp_path / "index.html").read_text()
    history = (tmp_path / "history.html").read_text()
    methodology = (tmp_path / "methodology.html").read_text()
    food_html = html.split("Food prices")[1].split("About this index")[0]

    assert snapshot["bugout_index"] == 57.11
    assert "57.11" in html
    assert "not in the BugOut Index" in food_html
    assert "No weight" in food_html or "no weight" in food_html
    assert "https://fred.stlouisfed.org/series/CPIUFDNS" in food_html
    assert "CUUR0000SAF1" in food_html
    assert "2026-08-01" in food_html
    assert "2.7" in food_html
    assert "Raw weight" not in food_html
    assert "not in the BugOut Index" in history
    assert "2026-08-01" in history
    assert "CPIUFDNS" in methodology
    assert "not applied" in methodology


def test_food_shadow_failure_still_publishes_the_locked_score(tmp_path, monkeypatch):
    import runtime.publish.render as render
    import runtime.publish.weekly_run as weekly

    docs = tmp_path / "docs"
    data = tmp_path / "data"
    docs.mkdir()
    raws = _published_raws()
    previous = {
        "publication_date": "2026-09-19",
        "food_shadow": {
            "status": "success",
            "in_bugout_index": False,
            "series_ids": dict(SERIES),
            "bls_series_ids": {"food_cpi_yoy": "CUUR0000SAF1"},
            "values": {"food_cpi_yoy": 2.7},
            "dates": {"food_cpi_yoy": "2026-08-01"},
            "observations": {
                "food_cpi_yoy": [{"date": "2026-08-01", "value": 2.7}],
            },
            "errors": [],
        },
    }
    (docs / "latest.json").write_text(json.dumps(previous))
    monkeypatch.setattr(weekly, "DOCS_DATA", docs)
    monkeypatch.setattr(weekly, "DATA_DIR", data)
    monkeypatch.setattr(
        weekly,
        "fetch_core_metrics",
        lambda: {
            metric: {"status": "success", "data": {metric: raw}, "fetched_at": "2026-08-01"}
            for metric, raw in raws.items()
        },
    )
    monkeypatch.setattr(weekly, "fetch_markets", lambda: {"status": "success", "data": {"gold_usd_per_oz": 1}})
    monkeypatch.setattr(weekly, "fetch_pulse", lambda: {"status": "success", "data": {}, "dates": {}})
    monkeypatch.setattr(weekly, "fetch_revisions", lambda: {"status": "success"})
    monkeypatch.setattr(
        weekly,
        "fetch_labor_shadow",
        lambda: {"status": "success", "in_bugout_index": False, "values": {}, "dates": {}, "errors": []},
    )
    monkeypatch.setattr(
        weekly,
        "fetch_food_shadow",
        lambda: {"status": "error", "message": "down", "values": {}, "dates": {}, "errors": ["down"]},
    )
    monkeypatch.setattr(render, "render_site", lambda _snapshot: None)
    monkeypatch.setattr(weekly, "publication_date_for", lambda now=None: "2026-09-23")

    assert weekly.main() == 0
    snapshot = json.loads((docs / "latest.json").read_text())
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    assert snapshot["food_shadow"]["status"] == "reused"
    assert snapshot["food_shadow"]["in_bugout_index"] is False
    assert snapshot["food_shadow"]["dates"]["food_cpi_yoy"] == "2026-08-01"
    assert snapshot["food_shadow"]["values"]["food_cpi_yoy"] == 2.7
    assert snapshot["food_shadow"]["reused_from"] == "2026-09-19"
    with (data / "food_shadow_history.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[-1]["date"] == "2026-09-23"
    assert rows[-1]["food_cpi_yoy"] == "2.7"
    assert rows[-1]["food_cpi_yoy_observation_date"] == "2026-08-01"
    assert "T" not in rows[-1]["food_cpi_yoy_observation_date"]


def test_markets_refusal_does_not_fetch_the_shadow_series(tmp_path, monkeypatch):
    import runtime.publish.weekly_run as weekly

    monkeypatch.setattr(weekly, "DOCS_DATA", tmp_path / "docs")
    monkeypatch.setattr(weekly, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(
        weekly,
        "fetch_core_metrics",
        lambda: {
            metric: {"status": "success", "data": {metric: 1.0}, "fetched_at": "2026-09-01"}
            for metric in weekly.CORE_METRICS
        },
    )
    monkeypatch.setattr(weekly, "fetch_markets", lambda: {"status": "error", "data": {}})
    monkeypatch.setattr(weekly, "fetch_pulse", lambda: {"status": "success", "data": {}})
    monkeypatch.setattr(weekly, "fetch_revisions", lambda: {"status": "success"})

    def _should_not_fetch():
        raise AssertionError("food shadow fetch ran after a markets refusal")

    monkeypatch.setattr(weekly, "fetch_food_shadow", _should_not_fetch)
    monkeypatch.setattr(weekly, "fetch_labor_shadow", lambda: {"status": "success", "values": {}})
    assert weekly.main() == EXIT_MARKETS_OR_PULSE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()


def test_committed_snapshot_keeps_the_score_and_fred_dates():
    latest = json.loads(LATEST.read_text())
    assert latest["bugout_index"] == 57.11
    assert latest["methodology_version"] == "1.0.0"
    assert latest["metrics"]["incident_rate"]["raw"] == 2723.0
    food = latest["food_shadow"]
    assert food["in_bugout_index"] is False
    assert food["series_ids"]["food_cpi_yoy"] == "CPIUFDNS"
    assert food["bls_series_ids"]["food_cpi_yoy"] == "CUUR0000SAF1"
    assert food["reading"] == "12-month percent change"
    observations = food["observations"]["food_cpi_yoy"]
    assert observations
    assert observations[-1]["date"] == food["dates"]["food_cpi_yoy"]
    assert observations[-1]["value"] == food["values"]["food_cpi_yoy"]
    assert "T" not in food["dates"]["food_cpi_yoy"]
    row = latest["history"]["food_shadow"][-1]
    assert row["date"] == latest["publication_date"]
    assert row["food_cpi_yoy_observation_date"] == food["dates"]["food_cpi_yoy"]
