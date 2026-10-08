# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""NYC DHS shelter census stays outside compute_index."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_nyc_dhs_shadow import (
    DATASET_ID,
    FIELD,
    SERIES,
    SOURCE_URL,
    assemble,
    fetch,
    parse_rows,
)
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index
from runtime.publish.failure_notice import EXIT_MARKETS_OR_PULSE_REFUSED
from runtime.publish.render import NYC_DHS_SHADOW_LABELS, render_site
from runtime.publish.week_note import build_week_note, unexplained_numerals
from runtime.publish.weekly_run import build_snapshot
from runtime.util.http_retry import RetryError

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
FORMULA = ROOT / "runtime" / "processing" / "formula.py"
PUBLISHED_DATE = "2026-09-19"
LOCKED_CORE = {
    "inflation_rate",
    "incident_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
}
SCORE_FIELDS = (
    "schema_version",
    "methodology_version",
    "publication_date",
    "bugout_index",
    "interpretation",
    "metrics",
)


def _published_raws() -> dict:
    with WEEKLY_CSV.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == PUBLISHED_DATE]
    assert len(rows) == 1
    return {metric: float(rows[0][metric]) for metric in CORE_METRICS}


def _payload(raws: dict) -> dict:
    return {metric: {"status": "success", "data": {metric: value}} for metric, value in raws.items()}


def _rows():
    return [
        {
            "date_of_census": "2026-09-25T00:00:00.000",
            "total_individuals_in_shelter": "84110",
            "total_individuals_in_families_with_children_in_shelter_": "52034",
        },
        {
            "date_of_census": "2026-09-24T00:00:00.000",
            "total_individuals_in_shelter": "83970",
        },
        {"date_of_census": "not-a-date", "total_individuals_in_shelter": "1"},
        {"date_of_census": "2026-09-23T00:00:00.000", "total_individuals_in_shelter": ""},
        {"date_of_census": "2026-09-22", "total_individuals_in_shelter": "1.5"},
    ]


def test_shadow_series_is_absent_from_compute_index_and_locked_score_holds():
    raws = _published_raws()
    assert set(CORE_METRICS) == LOCKED_CORE
    assert "nyc_dhs_total_individuals" not in CORE_METRICS
    assert "nyc_dhs_total_individuals" not in WEIGHTS
    assert "homelessness_rate" in CORE_METRICS
    formula = FORMULA.read_text()
    assert "k46n-sa2m" not in formula
    assert "total_individuals_in_shelter" not in formula
    assert "nyc_dhs" not in formula
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text()
    assert "def compute_index(" not in weekly

    plain = compute_index(_payload(raws))
    assert plain["index"] == 57.11
    assert plain["metrics"]["incident_rate"]["raw"] == 2723.0
    assert plain["metrics"]["homelessness_rate"]["raw"] == 0.23

    stuffed = _payload(raws)
    stuffed["nyc_dhs_total_individuals"] = {"data": {"nyc_dhs_total_individuals": 90000}}
    stuffed["nyc_dhs_shadow"] = {"data": {"total_individuals_in_shelter": 90000}}
    scored = compute_index(stuffed)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert scored["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert "nyc_dhs_total_individuals" not in scored["metrics"]
    assert list(scored["metrics"]) == list(CORE_METRICS)


def test_series_is_the_verified_nyc_total_not_the_family_subset():
    assert DATASET_ID == "k46n-sa2m"
    assert FIELD == "total_individuals_in_shelter"
    assert SERIES == {"nyc_dhs_total_individuals": "total_individuals_in_shelter"}
    assert list(SERIES) == list(NYC_DHS_SHADOW_LABELS)
    assert NYC_DHS_SHADOW_LABELS["nyc_dhs_total_individuals"][2] == FIELD
    assert "k46n-sa2m" in SOURCE_URL


def test_parse_keeps_census_dates_and_ignores_the_subset_column():
    rows = parse_rows(_rows())
    assert rows == [
        {"date": "2026-09-24", "value": 83970},
        {"date": "2026-09-25", "value": 84110},
    ]
    assert all("T" not in row["date"] for row in rows)
    assert all(row["value"] != 52034 for row in rows)


def test_fetch_failure_does_not_invent_a_date(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        raise RetryError("down")

    monkeypatch.setattr("runtime.data.fetch.fetch_nyc_dhs_shadow.get_with_retry", fake_get)
    payload = fetch()
    assert payload["status"] == "error"
    assert payload["in_bugout_index"] is False
    assert payload["geography"] == "New York City"
    assert payload["values"]["nyc_dhs_total_individuals"] is None
    assert payload["dates"] == {}
    blob = json.dumps(payload)
    assert "T" not in blob
    assert "2026-" not in blob
    assert "fetched_at" not in payload


def test_fetch_stores_the_census_date_and_the_total(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "k46n-sa2m" in url
        assert params["$select"] == "date_of_census,total_individuals_in_shelter"
        assert "total_individuals_in_families_with_children_in_shelter_" not in params["$select"]

        class Response:
            def json(self):
                return _rows()

        return Response()

    monkeypatch.setattr("runtime.data.fetch.fetch_nyc_dhs_shadow.get_with_retry", fake_get)
    payload = fetch()
    assert payload["status"] == "success"
    assert payload["in_bugout_index"] is False
    assert payload["dataset_id"] == "k46n-sa2m"
    assert payload["geography"] == "New York City"
    assert "not a U.S." in payload["scope"]
    assert payload["series_ids"] == {"nyc_dhs_total_individuals": "total_individuals_in_shelter"}
    assert payload["dates"] == {"nyc_dhs_total_individuals": "2026-09-25"}
    assert payload["values"]["nyc_dhs_total_individuals"] == 84110
    assert payload["observations"]["nyc_dhs_total_individuals"][-1] == {
        "date": "2026-09-25",
        "value": 84110,
    }
    assert "T" not in json.dumps(payload["dates"])
    assert "fetched_at" not in payload


def test_non_list_response_is_an_error(monkeypatch):
    def fake_get(_url, params=None, timeout=None):
        class Response:
            def json(self):
                return {"error": True, "message": "nope"}

        return Response()

    monkeypatch.setattr("runtime.data.fetch.fetch_nyc_dhs_shadow.get_with_retry", fake_get)
    payload = fetch()
    assert payload["status"] == "error"
    assert payload["values"]["nyc_dhs_total_individuals"] is None
    assert payload["in_bugout_index"] is False


def test_snapshot_records_the_shadow_series_without_changing_the_index():
    raws = _published_raws()
    scored = compute_index(_payload(raws))
    nyc = assemble(
        {"nyc_dhs_total_individuals": [{"date": "2026-09-25", "value": 84110}]},
        [],
    )
    nyc["in_bugout_index"] = True  # the publisher must force this back off
    snapshot = build_snapshot(
        PUBLISHED_DATE,
        scored,
        _payload(raws),
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
        None,
        None,
        nyc,
    )
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["methodology_version"] == "1.1.0"
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert snapshot["nyc_dhs_shadow"]["in_bugout_index"] is False
    assert snapshot["nyc_dhs_shadow"]["geography"] == "New York City"
    assert snapshot["nyc_dhs_shadow"]["dates"]["nyc_dhs_total_individuals"] == "2026-09-25"
    assert "nyc_dhs_total_individuals" not in snapshot["metrics"]


def test_week_note_mentions_the_shadow_series_only_as_companion_context():
    snapshot = json.loads(LATEST.read_text())
    snapshot["nyc_dhs_shadow"] = {
        "in_bugout_index": False,
        "geography": "New York City",
        "values": {"nyc_dhs_total_individuals": 84110},
        "dates": {"nyc_dhs_total_individuals": "2026-09-25"},
    }
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == []
    assert "NYC DHS shelter-census shadow series" in note[-1]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "84110" not in text
    assert "84,110" not in text
    assert "k46n-sa2m" not in text


def test_rendered_page_labels_the_census_as_nyc_only(tmp_path, monkeypatch):
    import runtime.publish.render as render

    snapshot = json.loads(LATEST.read_text())
    before = {key: snapshot[key] for key in SCORE_FIELDS}
    snapshot["nyc_dhs_shadow"] = assemble(
        {
            "nyc_dhs_total_individuals": [
                {"date": "2026-09-24", "value": 83970},
                {"date": "2026-09-25", "value": 84110},
            ],
        },
        [],
    )
    snapshot.setdefault("history", {})["nyc_dhs_shadow"] = [{
        "date": snapshot["publication_date"],
        "nyc_dhs_total_individuals": "84110",
        "nyc_dhs_total_individuals_observation_date": "2026-09-25",
    }]
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)
    html = (tmp_path / "index.html").read_text()
    history = (tmp_path / "history.html").read_text()
    methodology = (tmp_path / "methodology.html").read_text()
    nyc_html = html.split("NYC DHS shelter census")[1].split("About this index")[0]

    assert snapshot["bugout_index"] == before["bugout_index"] == 57.04
    assert snapshot["methodology_version"] == "1.0.0"
    assert {key: snapshot[key] for key in SCORE_FIELDS} == before
    assert "57.04" in html
    assert "New York City only" in nyc_html
    assert "not a U.S." in nyc_html
    assert "HUD AHAR" in nyc_html
    assert "not in the BugOut Index" in nyc_html
    assert "No weight" in nyc_html or "no weight" in nyc_html
    assert "https://data.cityofnewyork.us/Social-Services/DHS-Daily-Report/k46n-sa2m" in nyc_html
    assert "total_individuals_in_shelter" in nyc_html
    assert "2026-09-25" in nyc_html
    assert "84,110" in nyc_html
    assert "Raw weight" not in nyc_html
    assert "New York City only" in history
    assert "not a U.S. total" in history
    assert "not in the BugOut Index" in history
    assert "2026-09-25" in history
    assert "k46n-sa2m" in methodology
    assert "not a U.S. figure" in methodology
    assert "HUD AHAR" in methodology


def test_nyc_shadow_failure_still_publishes_the_locked_score(tmp_path, monkeypatch):
    import runtime.publish.render as render
    import runtime.publish.weekly_run as weekly

    docs = tmp_path / "docs"
    data = tmp_path / "data"
    docs.mkdir()
    raws = _published_raws()
    previous = {
        "publication_date": "2026-09-19",
        "nyc_dhs_shadow": {
            "status": "success",
            "in_bugout_index": False,
            "geography": "New York City",
            "dataset_id": DATASET_ID,
            "series_ids": dict(SERIES),
            "values": {"nyc_dhs_total_individuals": 84110},
            "dates": {"nyc_dhs_total_individuals": "2026-09-25"},
            "observations": {
                "nyc_dhs_total_individuals": [{"date": "2026-09-25", "value": 84110}],
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
        lambda: {"status": "success", "in_bugout_index": False, "values": {}, "dates": {}, "errors": []},
    )
    monkeypatch.setattr(
        weekly,
        "fetch_nyc_dhs_shadow",
        lambda: {"status": "error", "message": "down", "values": {}, "dates": {}, "errors": ["down"]},
    )
    for _name in (
        "fetch_ramsey_shelter_shadow",
        "fetch_shelter_region_shadow",
        "fetch_sf_shelter_shadow",
    ):
        monkeypatch.setattr(
            weekly,
            _name,
            lambda: {"status": "success", "in_bugout_index": False, "values": {}, "dates": {}, "errors": []},
        )
    monkeypatch.setattr(render, "render_site", lambda _snapshot: None)
    monkeypatch.setattr(weekly, "publication_date_for", lambda now=None: "2026-09-23")

    assert weekly.main() == 0
    snapshot = json.loads((docs / "latest.json").read_text())
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["methodology_version"] == "1.1.0"
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    assert snapshot["nyc_dhs_shadow"]["status"] == "reused"
    assert snapshot["nyc_dhs_shadow"]["in_bugout_index"] is False
    assert snapshot["nyc_dhs_shadow"]["dates"]["nyc_dhs_total_individuals"] == "2026-09-25"
    assert snapshot["nyc_dhs_shadow"]["values"]["nyc_dhs_total_individuals"] == 84110
    assert snapshot["nyc_dhs_shadow"]["reused_from"] == "2026-09-19"
    with (data / "nyc_dhs_shadow_history.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[-1]["date"] == "2026-09-23"
    assert rows[-1]["nyc_dhs_total_individuals"] == "84110"
    assert rows[-1]["nyc_dhs_total_individuals_observation_date"] == "2026-09-25"
    assert "T" not in rows[-1]["nyc_dhs_total_individuals_observation_date"]


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
        raise AssertionError("NYC DHS shadow fetch ran after a markets refusal")

    monkeypatch.setattr(weekly, "fetch_nyc_dhs_shadow", _should_not_fetch)
    monkeypatch.setattr(weekly, "fetch_labor_shadow", lambda: {"status": "success", "values": {}})
    monkeypatch.setattr(weekly, "fetch_food_shadow", lambda: {"status": "success", "values": {}})
    for _name in (
        "fetch_ramsey_shelter_shadow",
        "fetch_shelter_region_shadow",
        "fetch_sf_shelter_shadow",
    ):
        monkeypatch.setattr(weekly, _name, _should_not_fetch)
    assert weekly.main() == EXIT_MARKETS_OR_PULSE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()


def test_committed_snapshot_keeps_the_score_and_adds_only_the_companion():
    latest = json.loads(LATEST.read_text())
    assert latest["bugout_index"] == 57.04
    assert latest["methodology_version"] == "1.0.0"
    assert latest["metrics"]["incident_rate"]["raw"] == 2723.0
    assert latest["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert latest["metrics"]["trust_in_government"]["raw"] == 41.0
    nyc = latest["nyc_dhs_shadow"]
    assert nyc["in_bugout_index"] is False
    assert nyc["geography"] == "New York City"
    assert nyc["dataset_id"] == "k46n-sa2m"
    assert nyc["series_ids"]["nyc_dhs_total_individuals"] == "total_individuals_in_shelter"
    observations = nyc["observations"]["nyc_dhs_total_individuals"]
    assert observations
    assert observations[-1]["date"] == nyc["dates"]["nyc_dhs_total_individuals"]
    assert observations[-1]["value"] == nyc["values"]["nyc_dhs_total_individuals"]
    assert "T" not in nyc["dates"]["nyc_dhs_total_individuals"]
    assert nyc["dates"]["nyc_dhs_total_individuals"] <= latest["publication_date"]
    row = latest["history"]["nyc_dhs_shadow"][-1]
    assert row["date"] == latest["publication_date"]
    assert row["nyc_dhs_total_individuals_observation_date"] == nyc["dates"]["nyc_dhs_total_individuals"]
