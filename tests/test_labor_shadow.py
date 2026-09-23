# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Prime-age labor utilization stays outside compute_index."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_labor_shadow import (
    SERIES,
    assemble,
    fetch,
    parse_observations,
)
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index
from runtime.publish.failure_notice import EXIT_MARKETS_OR_PULSE_REFUSED
from runtime.publish.render import LABOR_SHADOW_LABELS, render_site
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
    assert "prime_age_epop" not in CORE_METRICS
    assert "prime_age_lfpr" not in CORE_METRICS
    assert "prime_age_epop" not in WEIGHTS
    assert "LNS12300060" not in (ROOT / "runtime" / "processing" / "formula.py").read_text()

    plain = compute_index(_payload(raws))
    assert plain["index"] == 57.11
    assert plain["metrics"]["incident_rate"]["raw"] == 2723.0
    assert raws["homelessness_rate"] == 0.23
    assert raws["trust_in_government"] == 41.0

    stuffed = _payload(raws)
    stuffed["prime_age_epop"] = {"data": {"prime_age_epop": 80.4}}
    stuffed["prime_age_lfpr"] = {"data": {"prime_age_lfpr": 83.4}}
    stuffed["labor_shadow"] = {"data": {"prime_age_epop": 50.0, "prime_age_lfpr": 50.0}}
    scored = compute_index(stuffed)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert "prime_age_epop" not in scored["metrics"]
    assert "prime_age_lfpr" not in scored["metrics"]
    assert list(scored["metrics"]) == list(CORE_METRICS)


def test_series_ids_match_the_verified_fred_pages():
    assert SERIES == {
        "prime_age_epop": "LNS12300060",
        "prime_age_lfpr": "LNS11300060",
    }
    assert list(SERIES) == list(LABOR_SHADOW_LABELS)
    for key, series_id in SERIES.items():
        assert LABOR_SHADOW_LABELS[key][2] == series_id


def test_parse_keeps_fred_dates_and_drops_placeholders():
    rows = parse_observations([
        {"date": "2026-08-01", "value": "80.4"},
        {"date": "2026-07-01", "value": "."},
        {"date": "2026-06-01", "value": "80.2"},
        {"observation_date": "not-a-date", "value": "1"},
    ])
    assert rows == [
        {"date": "2026-06-01", "value": 80.2},
        {"date": "2026-08-01", "value": 80.4},
    ]


def test_missing_api_key_does_not_invent_a_timestamp(monkeypatch):
    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_secret", lambda _key: None)
    payload = fetch()
    assert payload["status"] == "error"
    assert payload["in_bugout_index"] is False
    assert payload["dates"] == {}
    assert payload["values"]["prime_age_epop"] is None
    blob = json.dumps(payload)
    assert "T" not in blob
    assert "2026-" not in blob


def test_fetch_stores_fred_observation_dates(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        series_id = params["series_id"]

        class Response:
            def json(self):
                if series_id == "LNS12300060":
                    return {"observations": [
                        {"date": "2026-08-01", "value": "80.4"},
                        {"date": "2026-07-01", "value": "."},
                        {"date": "2026-06-01", "value": "80.2"},
                    ]}
                assert series_id == "LNS11300060"
                return {"observations": [
                    {"date": "2026-08-01", "value": "83.4"},
                    {"date": "2026-07-01", "value": "83.4"},
                ]}

        return Response()

    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_with_retry", fake_get)
    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_secret", lambda _key: "test-key")
    payload = fetch()
    assert payload["status"] == "success"
    assert payload["in_bugout_index"] is False
    assert payload["dates"] == {"prime_age_epop": "2026-08-01", "prime_age_lfpr": "2026-08-01"}
    assert payload["values"]["prime_age_epop"] == 80.4
    assert payload["values"]["prime_age_lfpr"] == 83.4
    assert [row["date"] for row in payload["observations"]["prime_age_epop"]] == [
        "2026-06-01",
        "2026-08-01",
    ]
    assert "fetched_at" not in payload
    assert "T" not in json.dumps(payload["dates"])


def test_one_series_failing_is_partial_and_does_not_invent_its_date(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        if params["series_id"] == "LNS11300060":
            raise RetryError("down")

        class Response:
            def json(self):
                return {"observations": [{"date": "2026-08-01", "value": "80.4"}]}

        return Response()

    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_with_retry", fake_get)
    monkeypatch.setattr("runtime.data.fetch.fetch_labor_shadow.get_secret", lambda _key: "test-key")
    payload = fetch()
    assert payload["status"] == "partial"
    assert payload["values"]["prime_age_epop"] == 80.4
    assert payload["values"]["prime_age_lfpr"] is None
    assert payload["dates"] == {"prime_age_epop": "2026-08-01"}
    assert payload["in_bugout_index"] is False


def test_snapshot_records_the_shadow_series_without_changing_the_index():
    raws = _published_raws()
    scored = compute_index(_payload(raws))
    labor = assemble(
        {
            "prime_age_epop": [{"date": "2026-08-01", "value": 80.4}],
            "prime_age_lfpr": [{"date": "2026-08-01", "value": 83.4}],
        },
        [],
    )
    labor["in_bugout_index"] = True  # the publisher must force this back off
    snapshot = build_snapshot(
        PUBLISHED_DATE,
        scored,
        _payload(raws),
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
        labor,
    )
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["labor_shadow"]["in_bugout_index"] is False
    assert snapshot["labor_shadow"]["dates"]["prime_age_epop"] == "2026-08-01"
    assert "prime_age_epop" not in snapshot["metrics"]


def test_week_note_mentions_the_shadow_series_only_as_companion_context():
    snapshot = json.loads(LATEST.read_text())
    snapshot["labor_shadow"] = {
        "in_bugout_index": False,
        "values": {"prime_age_epop": 80.4, "prime_age_lfpr": 83.4},
        "dates": {"prime_age_epop": "2026-08-01", "prime_age_lfpr": "2026-08-01"},
    }
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == []
    assert "labor-utilization shadow series" in note[-1]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "80.4" not in text
    assert "83.4" not in text
    assert "LNS12300060" not in text


def test_rendered_page_labels_the_shadow_series_outside_the_index(tmp_path, monkeypatch):
    import runtime.publish.render as render

    snapshot = json.loads(LATEST.read_text())
    snapshot["labor_shadow"] = assemble(
        {
            "prime_age_epop": [
                {"date": "2026-07-01", "value": 80.4},
                {"date": "2026-08-01", "value": 80.4},
            ],
            "prime_age_lfpr": [
                {"date": "2026-07-01", "value": 83.4},
                {"date": "2026-08-01", "value": 83.4},
            ],
        },
        [],
    )
    snapshot.setdefault("history", {})["labor_shadow"] = [{
        "date": snapshot["publication_date"],
        "prime_age_epop": "80.4",
        "prime_age_epop_observation_date": "2026-08-01",
        "prime_age_lfpr": "83.4",
        "prime_age_lfpr_observation_date": "2026-08-01",
    }]
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)
    html = (tmp_path / "index.html").read_text()
    history = (tmp_path / "history.html").read_text()
    methodology = (tmp_path / "methodology.html").read_text()
    labor_html = html.split("Labor utilization")[1].split("About this index")[0]

    assert snapshot["bugout_index"] == 57.11
    assert "57.11" in html
    assert "not in the BugOut Index" in labor_html
    assert "No weight" in labor_html or "no weight" in labor_html
    assert "https://fred.stlouisfed.org/series/LNS12300060" in labor_html
    assert "https://fred.stlouisfed.org/series/LNS11300060" in labor_html
    assert "2026-08-01" in labor_html
    assert "80.4" in labor_html
    assert "83.4" in labor_html
    assert "Raw weight" not in labor_html
    assert "not in the BugOut Index" in history
    assert "2026-08-01" in history
    assert "not in the BugOut Index" in methodology or "not in the score" in methodology
    assert "LNS12300060" in methodology


def test_labor_shadow_failure_still_publishes_the_locked_score(tmp_path, monkeypatch):
    import runtime.publish.render as render
    import runtime.publish.weekly_run as weekly

    docs = tmp_path / "docs"
    data = tmp_path / "data"
    docs.mkdir()
    raws = _published_raws()
    previous = {
        "publication_date": "2026-09-19",
        "labor_shadow": {
            "status": "success",
            "in_bugout_index": False,
            "series_ids": dict(SERIES),
            "values": {"prime_age_epop": 80.4, "prime_age_lfpr": 83.4},
            "dates": {"prime_age_epop": "2026-08-01", "prime_age_lfpr": "2026-08-01"},
            "observations": {
                "prime_age_epop": [{"date": "2026-08-01", "value": 80.4}],
                "prime_age_lfpr": [{"date": "2026-08-01", "value": 83.4}],
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
    assert snapshot["labor_shadow"]["status"] == "reused"
    assert snapshot["labor_shadow"]["in_bugout_index"] is False
    assert snapshot["labor_shadow"]["dates"]["prime_age_epop"] == "2026-08-01"
    assert snapshot["labor_shadow"]["values"]["prime_age_epop"] == 80.4
    assert snapshot["labor_shadow"]["reused_from"] == "2026-09-19"
    with (data / "labor_shadow_history.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[-1]["date"] == "2026-09-23"
    assert rows[-1]["prime_age_epop_observation_date"] == "2026-08-01"
    assert rows[-1]["prime_age_lfpr_observation_date"] == "2026-08-01"
    assert "T" not in rows[-1]["prime_age_epop_observation_date"]


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
        raise AssertionError("labor shadow fetch ran after a markets refusal")

    monkeypatch.setattr(weekly, "fetch_labor_shadow", _should_not_fetch)
    assert weekly.main() == EXIT_MARKETS_OR_PULSE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()


def test_committed_snapshot_keeps_the_score_and_fred_dates():
    latest = json.loads(LATEST.read_text())
    assert latest["bugout_index"] == 57.11
    assert latest["methodology_version"] == "1.0.0"
    assert latest["metrics"]["incident_rate"]["raw"] == 2723.0
    assert latest["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert latest["metrics"]["trust_in_government"]["raw"] == 41.0
    labor = latest["labor_shadow"]
    assert labor["in_bugout_index"] is False
    assert labor["series_ids"]["prime_age_epop"] == "LNS12300060"
    assert labor["series_ids"]["prime_age_lfpr"] == "LNS11300060"
    for key in SERIES:
        observations = labor["observations"][key]
        assert observations
        assert observations[-1]["date"] == labor["dates"][key]
        assert observations[-1]["value"] == labor["values"][key]
        assert "T" not in labor["dates"][key]
    row = latest["history"]["labor_shadow"][-1]
    assert row["date"] == latest["publication_date"]
    assert row["prime_age_epop_observation_date"] == labor["dates"]["prime_age_epop"]
    assert row["prime_age_lfpr_observation_date"] == labor["dates"]["prime_age_lfpr"]
