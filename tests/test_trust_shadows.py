# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Pew and Gallup trust companions stay outside compute_index."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_gallup_confidence_shadow import (
    SERIES as GALLUP_SERIES,
    SOURCE_URL as GALLUP_HOME,
    fetch as fetch_gallup,
)
from runtime.data.fetch.fetch_pew_trust_shadow import (
    SERIES as PEW_SERIES,
    SOURCE_URL as PEW_URL,
    fetch as fetch_pew,
)
from runtime.data.fetch.manual_checklist import ChecklistError, load_series
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index
from runtime.publish.failure_notice import EXIT_MARKETS_OR_PULSE_REFUSED
from runtime.publish.render import (
    GALLUP_CONFIDENCE_SHADOW_LABELS,
    PEW_TRUST_SHADOW_LABELS,
    render_site,
)
from runtime.publish.week_note import build_week_note, unexplained_numerals
from runtime.publish.weekly_run import build_snapshot

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
ANNUAL = ROOT / "runtime" / "data" / "annual_inputs.csv"
PEW_CSV = ROOT / "runtime" / "data" / "pew_trust_shadow.csv"
GALLUP_CSV = ROOT / "runtime" / "data" / "gallup_confidence_shadow.csv"
FORMULA = ROOT / "runtime" / "processing" / "formula.py"
PUBLISHED_DATE = "2026-09-19"
SCORE_FIELDS = (
    "schema_version",
    "methodology_version",
    "publication_date",
    "bugout_index",
    "interpretation",
    "metrics",
)
HEADER = (
    "series,value,observation_period,observation_date,source,source_url,reviewed_at\n"
)
PEW_ROW = (
    "pew_public_trust,17,September 22-28 2025,2025-09-28,"
    "Pew Research Center Public Trust in Government 1958-2025,"
    "https://www.pewresearch.org/politics/2025/12/04/public-trust-in-government-1958-2025/,"
    "2026-10-06\n"
)


def _published_raws() -> dict:
    with WEEKLY_CSV.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == PUBLISHED_DATE]
    assert len(rows) == 1
    return {metric: float(rows[0][metric]) for metric in CORE_METRICS}


def _payload(raws: dict) -> dict:
    return {metric: {"status": "success", "data": {metric: value}} for metric, value in raws.items()}


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(HEADER + body)
    return path


def test_shadows_are_absent_from_compute_index_and_edelman_stays_the_core_input():
    raws = _published_raws()
    assert set(CORE_METRICS) == {
        "inflation_rate",
        "incident_rate",
        "unemployment_rate",
        "debt_to_gdp_ratio",
        "homelessness_rate",
        "trust_in_government",
    }
    for key in ("pew_public_trust", "gallup_congress", "gallup_presidency", "gallup_supreme_court", "gallup_core_institutions"):
        assert key not in CORE_METRICS
        assert key not in WEIGHTS
    formula = FORMULA.read_text()
    assert "pew_public_trust" not in formula
    assert "gallup_congress" not in formula
    assert "pewresearch.org" not in formula
    assert "gallup.com" not in formula
    annual = ANNUAL.read_text()
    assert "trust_in_government,41,2025,2025," in annual
    assert "pew_public_trust" not in annual
    assert "gallup_congress" not in annual

    plain = compute_index(_payload(raws))
    assert plain["index"] == 57.11
    assert plain["metrics"]["incident_rate"]["raw"] == 2723.0
    assert plain["metrics"]["trust_in_government"]["raw"] == 41.0

    stuffed = _payload(raws)
    stuffed["pew_public_trust"] = {"data": {"pew_public_trust": 17}}
    stuffed["pew_trust_shadow"] = {"data": {"pew_public_trust": 17}}
    stuffed["gallup_congress"] = {"data": {"gallup_congress": 9}}
    stuffed["gallup_confidence_shadow"] = {"data": {"gallup_presidency": 27}}
    scored = compute_index(stuffed)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert scored["metrics"]["trust_in_government"]["raw"] == 41.0
    assert "pew_public_trust" not in scored["metrics"]
    assert "gallup_congress" not in scored["metrics"]
    assert list(scored["metrics"]) == list(CORE_METRICS)


def test_fetchers_read_the_checklist_and_do_not_request_the_publishers():
    pew_source = (ROOT / "runtime/data/fetch/fetch_pew_trust_shadow.py").read_text()
    gallup_source = (ROOT / "runtime/data/fetch/fetch_gallup_confidence_shadow.py").read_text()
    for source in (pew_source, gallup_source):
        assert "get_with_retry" not in source
        assert "requests" not in source
    assert "news.gallup.com" not in gallup_source.split("SOURCE_URL", 1)[0]
    assert list(PEW_SERIES) == list(PEW_TRUST_SHADOW_LABELS)
    assert list(GALLUP_SERIES) == list(GALLUP_CONFIDENCE_SHADOW_LABELS)
    assert PEW_URL.startswith("https://www.pewresearch.org/")
    assert GALLUP_HOME == "https://news.gallup.com/poll/1597/confidence-institutions.aspx"


def test_committed_checklists_match_the_cited_waves():
    pew = fetch_pew()
    assert pew["status"] == "success"
    assert pew["in_bugout_index"] is False
    assert pew["values"]["pew_public_trust"] == 17
    assert isinstance(pew["values"]["pew_public_trust"], int)
    assert pew["dates"] == {"pew_public_trust": "2025-09-28"}
    assert pew["periods"]["pew_public_trust"] == "September 22-28 2025"
    assert pew["reviewed_at"]["pew_public_trust"] == "2026-10-06"
    assert pew["source_urls"]["pew_public_trust"] == PEW_URL
    assert pew["observations"]["pew_public_trust"] == [
        {"date": "2024-05-19", "value": 22},
        {"date": "2025-02-09", "value": 17},
        {"date": "2025-09-28", "value": 17},
    ]
    assert "T" not in json.dumps(pew["dates"])
    assert "fetched_at" not in pew
    assert "Edelman" in pew["levels_note"]

    gallup = fetch_gallup()
    assert gallup["status"] == "success"
    assert gallup["in_bugout_index"] is False
    assert gallup["values"] == {
        "gallup_congress": 9,
        "gallup_presidency": 27,
        "gallup_supreme_court": 27,
        "gallup_core_institutions": 27,
    }
    assert all(isinstance(value, int) for value in gallup["values"].values())
    assert gallup["dates"] == {
        "gallup_congress": "2026-06-15",
        "gallup_presidency": "2026-06-15",
        "gallup_supreme_court": "2026-06-15",
        "gallup_core_institutions": "2026-06-15",
    }
    assert gallup["periods"]["gallup_congress"] == "June 1-15 2026"
    assert "712436" in gallup["source_urls"]["gallup_congress"]
    assert "permission" in gallup["license_note"]
    assert "since 1993" in gallup["average_definition"]
    assert len(gallup["observations"]["gallup_congress"]) == 1
    assert "fetched_at" not in gallup


def test_missing_pew_row_fails_closed(tmp_path):
    path = _write(tmp_path, "pew.csv", "")
    payload = fetch_pew(path)
    assert payload["status"] == "error"
    assert payload["in_bugout_index"] is False
    assert payload["values"]["pew_public_trust"] is None
    assert payload["dates"] == {}
    assert "missing series" in payload["message"]
    blob = json.dumps(payload)
    assert "T00:00:00" not in blob
    assert "2026-" not in blob
    assert payload["dates"] == {}
    assert "fetched_at" not in payload


def test_missing_gallup_institution_fails_closed_without_partial_values(tmp_path):
    body = (
        "gallup_congress,9,June 1-15 2026,2026-06-15,Gallup,"
        "https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,"
        "2026-10-06\n"
        "gallup_presidency,27,June 1-15 2026,2026-06-15,Gallup,"
        "https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,"
        "2026-10-06\n"
    )
    payload = fetch_gallup(_write(tmp_path, "gallup.csv", body))
    assert payload["status"] == "error"
    assert payload["in_bugout_index"] is False
    assert all(value is None for value in payload["values"].values())
    assert payload["dates"] == {}
    assert "gallup_supreme_court" in payload["message"]
    assert "fetched_at" not in payload


def test_bad_checklist_cells_fail_closed(tmp_path):
    cases = [
        "pew_public_trust,,September 22-28 2025,2025-09-28,Pew,https://www.pewresearch.org/x,2026-10-06\n",
        "pew_public_trust,17,September 22-28 2025,2025-09-28T00:00:00Z,Pew,https://www.pewresearch.org/x,2026-10-06\n",
        "pew_public_trust,17,September 22-28 2025,not-a-date,Pew,https://www.pewresearch.org/x,2026-10-06\n",
        "pew_public_trust,17,September 22-28 2025,2025-09-28,Pew,https://www.pewresearch.org/x,2026-10-06T00:00:00Z\n",
        "pew_public_trust,101,September 22-28 2025,2025-09-28,Pew,https://www.pewresearch.org/x,2026-10-06\n",
        "pew_public_trust,17,,2025-09-28,Pew,https://www.pewresearch.org/x,2026-10-06\n",
        "pew_public_trust,17,September 22-28 2025,2025-09-28,Pew,not-a-url,2026-10-06\n",
        "pew_public_trust,17,September 22-28 2025,2025-09-28,Pew,https://www.pewresearch.org/x,2025-01-01\n",
        "other_series,17,September 22-28 2025,2025-09-28,Pew,https://www.pewresearch.org/x,2026-10-06\n",
    ]
    for body in cases:
        payload = fetch_pew(_write(tmp_path, "pew.csv", body))
        assert payload["status"] == "error", body
        assert payload["values"]["pew_public_trust"] is None
        assert payload["dates"] == {}
        assert payload["in_bugout_index"] is False


def test_duplicate_pew_date_and_a_second_gallup_year_fail_closed(tmp_path):
    duplicated = PEW_ROW + PEW_ROW
    payload = fetch_pew(_write(tmp_path, "pew.csv", duplicated))
    assert payload["status"] == "error"
    assert "observation_date" in payload["message"]

    two_years = (
        "gallup_congress,10,June 2025,2025-06-15,Gallup,https://news.gallup.com/poll/1597/confidence-institutions.aspx,2026-10-06\n"
        "gallup_congress,9,June 1-15 2026,2026-06-15,Gallup,https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,2026-10-06\n"
        "gallup_presidency,27,June 1-15 2026,2026-06-15,Gallup,https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,2026-10-06\n"
        "gallup_supreme_court,27,June 1-15 2026,2026-06-15,Gallup,https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,2026-10-06\n"
        "gallup_core_institutions,27,June 1-15 2026,2026-06-15,Gallup,https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx,2026-10-06\n"
    )
    payload = fetch_gallup(_write(tmp_path, "gallup.csv", two_years))
    assert payload["status"] == "error"
    assert "at most 1" in payload["message"]
    assert payload["values"]["gallup_congress"] is None


def test_missing_checklist_file_fails_closed(tmp_path):
    payload = fetch_pew(tmp_path / "missing.csv")
    assert payload["status"] == "error"
    assert payload["values"]["pew_public_trust"] is None
    assert "missing" in payload["message"]
    try:
        load_series(
            tmp_path / "missing.csv",
            required=("pew_public_trust",),
            max_rows_per_series=12,
            label="Pew public trust",
        )
    except ChecklistError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("missing checklist should fail closed")


def test_snapshot_records_the_companions_without_changing_the_index():
    raws = _published_raws()
    scored = compute_index(_payload(raws))
    pew = fetch_pew()
    gallup = fetch_gallup()
    pew["in_bugout_index"] = True
    gallup["in_bugout_index"] = True
    snapshot = build_snapshot(
        PUBLISHED_DATE,
        scored,
        _payload(raws),
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
        None,
        None,
        None,
        pew,
        gallup,
    )
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["methodology_version"] == "1.0.0"
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    assert snapshot["pew_trust_shadow"]["in_bugout_index"] is False
    assert snapshot["gallup_confidence_shadow"]["in_bugout_index"] is False
    assert snapshot["pew_trust_shadow"]["dates"]["pew_public_trust"] == "2025-09-28"
    assert snapshot["gallup_confidence_shadow"]["values"]["gallup_congress"] == 9
    assert "pew_public_trust" not in snapshot["metrics"]
    assert "gallup_congress" not in snapshot["metrics"]


def test_week_note_names_the_companions_without_their_percents():
    snapshot = json.loads(LATEST.read_text())
    snapshot["pew_trust_shadow"] = fetch_pew()
    snapshot["gallup_confidence_shadow"] = fetch_gallup()
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == []
    assert "Pew public-trust shadow series" in note[-1]
    assert "Gallup confidence shadow series" in note[-1]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "17%" not in text
    assert "22%" not in text
    assert "2025-09-28" not in text
    assert "2026-06-15" not in text


def test_rendered_page_labels_the_companions_outside_the_score(tmp_path, monkeypatch):
    import runtime.publish.render as render

    snapshot = json.loads(LATEST.read_text())
    before = {key: snapshot[key] for key in SCORE_FIELDS}
    snapshot["pew_trust_shadow"] = fetch_pew()
    snapshot["gallup_confidence_shadow"] = fetch_gallup()
    snapshot.setdefault("history", {})["pew_trust_shadow"] = [{
        "date": snapshot["publication_date"],
        "pew_public_trust": "17",
        "pew_public_trust_observation_date": "2025-09-28",
    }]
    snapshot.setdefault("history", {})["gallup_confidence_shadow"] = [{
        "date": snapshot["publication_date"],
        "gallup_congress": "9",
        "gallup_congress_observation_date": "2026-06-15",
        "gallup_presidency": "27",
        "gallup_presidency_observation_date": "2026-06-15",
        "gallup_supreme_court": "27",
        "gallup_supreme_court_observation_date": "2026-06-15",
        "gallup_core_institutions": "27",
        "gallup_core_institutions_observation_date": "2026-06-15",
    }]
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)
    html = (tmp_path / "index.html").read_text()
    history = (tmp_path / "history.html").read_text()
    methodology = (tmp_path / "methodology.html").read_text()
    pew_html = html.split("Pew public trust")[1].split("Gallup confidence")[0]
    gallup_html = html.split("Gallup confidence in institutions")[1].split("About this index")[0]

    assert {key: snapshot[key] for key in SCORE_FIELDS} == before
    assert str(before["bugout_index"]) in html
    assert "companion · not in the BugOut Index" in pew_html
    assert "not interchangeable" in pew_html
    assert "41" in pew_html
    assert PEW_URL in pew_html
    assert "2025-09-28" in pew_html
    assert "September 22-28 2025" in pew_html
    assert "17 %" in pew_html
    assert "Raw weight" not in pew_html
    assert "stale" not in pew_html.lower()
    assert "companion · not in the BugOut Index" in gallup_html
    assert "may require permission" in gallup_html
    assert "not a republication" in gallup_html
    assert "https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx" in gallup_html
    assert "2026-06-15" in gallup_html
    assert "Congress" in gallup_html
    assert "14 institutions since 1993" in gallup_html
    assert "Raw weight" not in gallup_html
    assert "not in the BugOut Index" in history
    assert "2025-09-28" in history
    assert "2026-06-15" in history
    assert "not interchangeable" in methodology
    assert "Edelman" in methodology


def test_companion_failure_still_publishes_the_locked_score(tmp_path, monkeypatch):
    import runtime.publish.render as render
    import runtime.publish.weekly_run as weekly

    docs = tmp_path / "docs"
    data = tmp_path / "data"
    docs.mkdir()
    raws = _published_raws()
    previous = {
        "publication_date": "2026-09-19",
        "pew_trust_shadow": fetch_pew(),
        "gallup_confidence_shadow": fetch_gallup(),
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
        lambda: {"status": "success", "in_bugout_index": False, "values": {}, "dates": {}, "errors": []},
    )
    monkeypatch.setattr(
        weekly,
        "fetch_pew_trust_shadow",
        lambda: {"status": "error", "message": "checklist missing", "values": {}, "dates": {}, "errors": ["checklist missing"]},
    )
    monkeypatch.setattr(
        weekly,
        "fetch_gallup_confidence_shadow",
        lambda: {"status": "error", "message": "checklist missing", "values": {}, "dates": {}, "errors": ["checklist missing"]},
    )
    monkeypatch.setattr(render, "render_site", lambda _snapshot: None)
    monkeypatch.setattr(weekly, "publication_date_for", lambda now=None: "2026-09-23")

    assert weekly.main() == 0
    snapshot = json.loads((docs / "latest.json").read_text())
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["methodology_version"] == "1.0.0"
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    assert snapshot["pew_trust_shadow"]["status"] == "reused"
    assert snapshot["pew_trust_shadow"]["in_bugout_index"] is False
    assert snapshot["pew_trust_shadow"]["values"]["pew_public_trust"] == 17
    assert snapshot["pew_trust_shadow"]["dates"]["pew_public_trust"] == "2025-09-28"
    assert snapshot["pew_trust_shadow"]["reused_from"] == "2026-09-19"
    assert snapshot["gallup_confidence_shadow"]["status"] == "reused"
    assert snapshot["gallup_confidence_shadow"]["in_bugout_index"] is False
    assert snapshot["gallup_confidence_shadow"]["values"]["gallup_congress"] == 9
    assert snapshot["gallup_confidence_shadow"]["reused_from"] == "2026-09-19"
    with (data / "pew_trust_shadow_history.csv").open(newline="") as handle:
        pew_rows = list(csv.DictReader(handle))
    assert pew_rows[-1]["date"] == "2026-09-23"
    assert pew_rows[-1]["pew_public_trust"] == "17"
    assert pew_rows[-1]["pew_public_trust_observation_date"] == "2025-09-28"
    with (data / "gallup_confidence_shadow_history.csv").open(newline="") as handle:
        gallup_rows = list(csv.DictReader(handle))
    assert gallup_rows[-1]["gallup_congress"] == "9"
    assert gallup_rows[-1]["gallup_congress_observation_date"] == "2026-06-15"
    assert "T" not in gallup_rows[-1]["gallup_presidency_observation_date"]


def test_markets_refusal_does_not_fetch_the_trust_companions(tmp_path, monkeypatch):
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

    def _should_not_fetch_pew():
        raise AssertionError("Pew shadow fetch ran after a markets refusal")

    def _should_not_fetch_gallup():
        raise AssertionError("Gallup shadow fetch ran after a markets refusal")

    monkeypatch.setattr(weekly, "fetch_pew_trust_shadow", _should_not_fetch_pew)
    monkeypatch.setattr(weekly, "fetch_gallup_confidence_shadow", _should_not_fetch_gallup)
    monkeypatch.setattr(weekly, "fetch_labor_shadow", lambda: {"status": "success", "values": {}})
    monkeypatch.setattr(weekly, "fetch_food_shadow", lambda: {"status": "success", "values": {}})
    monkeypatch.setattr(weekly, "fetch_nyc_dhs_shadow", lambda: {"status": "success", "values": {}})
    assert weekly.main() == EXIT_MARKETS_OR_PULSE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()


def test_committed_snapshot_keeps_the_score_and_adds_the_companions():
    latest = json.loads(LATEST.read_text())
    assert latest["bugout_index"] == 57.04
    assert latest["methodology_version"] == "1.0.0"
    assert latest["publication_date"] == "2026-10-02"
    assert latest["metrics"]["incident_rate"]["raw"] == 2723.0
    assert latest["metrics"]["trust_in_government"]["raw"] == 41.0
    assert latest["metrics"]["trust_in_government"]["observation_date"] == "2025"
    pew = latest["pew_trust_shadow"]
    gallup = latest["gallup_confidence_shadow"]
    assert pew["in_bugout_index"] is False
    assert gallup["in_bugout_index"] is False
    assert pew["values"]["pew_public_trust"] == 17
    assert pew["dates"]["pew_public_trust"] == "2025-09-28"
    assert gallup["values"]["gallup_congress"] == 9
    assert gallup["values"]["gallup_presidency"] == 27
    assert gallup["values"]["gallup_supreme_court"] == 27
    assert gallup["values"]["gallup_core_institutions"] == 27
    assert "pew_public_trust" not in latest["metrics"]
    assert "gallup_congress" not in latest["metrics"]
    pew_row = latest["history"]["pew_trust_shadow"][-1]
    assert pew_row["date"] == latest["publication_date"]
    assert pew_row["pew_public_trust_observation_date"] == "2025-09-28"
    gallup_row = latest["history"]["gallup_confidence_shadow"][-1]
    assert gallup_row["date"] == latest["publication_date"]
    assert gallup_row["gallup_congress"] == "9"
