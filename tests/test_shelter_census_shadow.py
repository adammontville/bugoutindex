# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Local shelter companions stay outside compute_index."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_ramsey_shelter_shadow import (
    DATASET_ID as RAMSEY_DATASET,
    REQUIRED_TYPES,
    SERIES as RAMSEY_SERIES,
    SOURCE_URL as RAMSEY_URL,
    assemble as assemble_ramsey,
    fetch as fetch_ramsey,
    parse_rows as parse_ramsey,
)
from runtime.data.fetch.fetch_sf_shelter_shadow import (
    DATASET_ID as SF_DATASET,
    MEASURE_CODE,
    SERIES as SF_SERIES,
    SOURCE_URL as SF_URL,
    assemble as assemble_sf,
    fetch as fetch_sf,
    parse_rows as parse_sf,
    percent_points,
)
from runtime.data.fetch.fetch_shelter_region_shadow import (
    SERIES as REGION_SERIES,
    fetch as fetch_region,
)
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index
from runtime.publish.render import (
    RAMSEY_SHELTER_SHADOW_LABELS,
    SF_SHELTER_SHADOW_LABELS,
    SHELTER_REGION_SHADOW_LABELS,
    render_site,
)
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


def test_shadow_series_are_absent_from_compute_index_and_locked_score_holds():
    raws = _published_raws()
    assert set(CORE_METRICS) == LOCKED_CORE
    for name in (
        "ramsey_shelter_total_people",
        "nashville_hmis_people",
        "austin_sheltered_people",
        "denver_shelter_occupancy",
        "sf_shelter_occupancy_rate",
    ):
        assert name not in CORE_METRICS
        assert name not in WEIGHTS
    formula = FORMULA.read_text()
    for token in ("9mck-bcqu", "population_enrollees", "kc49-udxn", "ramsey_shelter", "sf_shelter", "nashville_hmis"):
        assert token not in formula

    plain = compute_index(_payload(raws))
    assert plain["index"] == 57.11
    assert plain["metrics"]["incident_rate"]["raw"] == 2723.0
    assert plain["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert plain["metrics"]["trust_in_government"]["raw"] == 41.0

    stuffed = _payload(raws)
    stuffed["ramsey_shelter_total_people"] = {"data": {"ramsey_shelter_total_people": 999}}
    stuffed["nashville_hmis_people"] = {"data": {"nashville_hmis_people": 999}}
    stuffed["sf_shelter_occupancy_rate"] = {"data": {"sf_shelter_occupancy_rate": 99}}
    stuffed["ramsey_shelter_shadow"] = {"data": {"population_enrollees": 999}}
    scored = compute_index(stuffed)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert scored["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert scored["metrics"]["trust_in_government"]["raw"] == 41.0
    assert "ramsey_shelter_total_people" not in scored["metrics"]
    assert list(scored["metrics"]) == list(CORE_METRICS)


def test_series_ids_match_the_verified_public_fields():
    assert RAMSEY_DATASET == "9mck-bcqu"
    assert RAMSEY_SERIES == {"ramsey_shelter_total_people": "population_enrollees"}
    assert list(RAMSEY_SERIES) == list(RAMSEY_SHELTER_SHADOW_LABELS)
    assert "9mck-bcqu" in RAMSEY_URL
    assert REQUIRED_TYPES == frozenset({
        "Families", "Single Men", "Single Women", "Youth (18-24)",
    })

    assert set(REGION_SERIES) == {
        "nashville_hmis_people",
        "austin_sheltered_people",
        "denver_shelter_occupancy",
    }
    assert list(REGION_SERIES) == list(SHELTER_REGION_SHADOW_LABELS)

    assert SF_DATASET == "kc49-udxn"
    assert MEASURE_CODE == "279"
    assert SF_SERIES == {"sf_shelter_occupancy_rate": "279"}
    assert list(SF_SERIES) == list(SF_SHELTER_SHADOW_LABELS)
    assert "kc49-udxn" in SF_URL


def test_ramsey_sum_requires_every_household_type_and_keeps_the_month_stamp():
    rows = []
    for month, values in (
        ("2026-08-01T00:00:00.000", {"Families": "47", "Single Men": "337", "Single Women": "80", "Youth (18-24)": "16"}),
        ("2026-07-01T00:00:00.000", {"Families": "47", "Single Men": "345", "Single Women": "82", "Youth (18-24)": "17"}),
    ):
        for kind, count in values.items():
            rows.append({
                "month_year": month,
                "family_type": kind,
                "population_enrollees": count,
                "utilization_rate": "0.9",
            })
    rows.append({
        "month_year": "2026-06-01T00:00:00.000",
        "family_type": "Families",
        "population_enrollees": "40",
    })
    rows.append({
        "month_year": "2026-05-01T00:00:00.000",
        "family_type": "Families",
        "population_enrollees": "1",
    })
    rows.append({
        "month_year": "2026-05-01T00:00:00.000",
        "family_type": "Families",
        "population_enrollees": "2",
    })
    parsed = parse_ramsey(rows)
    assert parsed == [
        {"date": "2026-07-01", "value": 491},
        {"date": "2026-08-01", "value": 480},
    ]
    payload = assemble_ramsey({"ramsey_shelter_total_people": parsed}, [])
    assert payload["in_bugout_index"] is False
    assert payload["geography"] == "Ramsey County, Minnesota"
    assert payload["values"]["ramsey_shelter_total_people"] == 480
    assert payload["dates"]["ramsey_shelter_total_people"] == "2026-08-01"
    assert "T" not in payload["dates"]["ramsey_shelter_total_people"]


def test_regional_checklist_keeps_cited_figures_and_fails_closed(tmp_path):
    payload = fetch_region()
    assert payload["status"] == "success"
    assert payload["in_bugout_index"] is False
    assert payload["values"]["nashville_hmis_people"] == 2907
    assert payload["dates"]["nashville_hmis_people"] == "2026-07-31"
    assert payload["values"]["austin_sheltered_people"] == 1070
    assert payload["dates"]["austin_sheltered_people"] == "2025-07-01"
    assert "2025-09-10" in payload["periods"]["austin_sheltered_people"]
    assert payload["values"]["denver_shelter_occupancy"] == 93
    assert payload["dates"]["denver_shelter_occupancy"] == "2026-06-30"
    assert "Nashville" in payload["measures"]["nashville_hmis_people"]
    assert "not a one-night" in payload["measures"]["nashville_hmis_people"]
    assert "lag" in payload["measures"]["austin_sheltered_people"]
    assert "Not a count of distinct" in payload["measures"]["denver_shelter_occupancy"]

    broken = tmp_path / "shelter_region_shadow.csv"
    broken.write_text(
        "series,value,observation_period,observation_date,source,source_url,reviewed_at\n"
        "nashville_hmis_people,2907.5,July 2026,2026-07-31,OHS,https://www.nashville.gov/x,2026-10-07\n"
        "austin_sheltered_people,1070,June 2025,2025-07-01,ECHO,https://echoatx.github.io/hrs-dashboard-site/,2026-10-07\n"
        "denver_shelter_occupancy,93,Q2 2026,2026-06-30,HOST,https://www.denvergov.org/x,2026-10-07\n"
    )
    failed = fetch_region(broken)
    assert failed["status"] == "error"
    assert failed["in_bugout_index"] is False
    assert failed["values"]["nashville_hmis_people"] is None
    assert "whole number" in failed["message"]


def test_sf_ratio_becomes_percent_and_a_headcount_shaped_value_is_dropped():
    assert percent_points("0.91") == 91.0
    assert percent_points("0.9") == 90.0
    assert percent_points("90") is None
    assert percent_points("") is None
    rows = [
        {"measure_code": "279", "calendar_month": "2026-08-31T00:00:00.000", "actual": "0.9"},
        {"measure_code": "279", "calendar_month": "2026-09-30T00:00:00.000", "actual": None},
        {"measure_code": "279", "calendar_month": "2026-07-31T00:00:00.000", "actual": "0.91"},
        {"measure_code": "7274", "calendar_month": "2026-07-31T00:00:00.000", "actual": "4957"},
        {"measure_code": "279", "calendar_month": "2026-08-31T00:00:00.000", "actual": "0.5"},
    ]
    parsed = parse_sf(rows)
    assert parsed == [
        {"date": "2026-07-31", "value": 91.0},
        {"date": "2026-08-31", "value": 90.0},
    ]
    payload = assemble_sf({"sf_shelter_occupancy_rate": parsed}, [])
    assert payload["in_bugout_index"] is False
    assert payload["geography"] == "San Francisco"
    assert payload["unit"] == "percent"
    assert payload["measure_code"] == "279"
    assert "not a headcount" in payload["scope"]
    assert payload["values"]["sf_shelter_occupancy_rate"] == 90.0
    assert payload["dates"]["sf_shelter_occupancy_rate"] == "2026-08-31"


def test_fetch_failures_stay_outside_the_score(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RetryError("down")

    monkeypatch.setattr("runtime.data.fetch.fetch_ramsey_shelter_shadow.get_with_retry", boom)
    monkeypatch.setattr("runtime.data.fetch.fetch_sf_shelter_shadow.get_with_retry", boom)
    for payload in (fetch_ramsey(), fetch_sf()):
        assert payload["status"] == "error"
        assert payload["in_bugout_index"] is False
        assert next(iter(payload["values"].values())) is None


def test_snapshot_keeps_the_locked_score_when_companions_are_attached():
    raws = _published_raws()
    scored = compute_index(_payload(raws))
    ramsey = assemble_ramsey(
        {"ramsey_shelter_total_people": [{"date": "2026-08-01", "value": 480}]},
        [],
    )
    region = fetch_region()
    region["in_bugout_index"] = True
    sf_shelter = assemble_sf(
        {"sf_shelter_occupancy_rate": [{"date": "2026-08-31", "value": 90.0}]},
        [],
    )
    ramsey["in_bugout_index"] = True
    snapshot = build_snapshot(
        PUBLISHED_DATE,
        scored,
        _payload(raws),
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
        None,
        None,
        None,
        extra_shadows={
            "ramsey_shelter_shadow": ramsey,
            "shelter_region_shadow": region,
            "sf_shelter_shadow": sf_shelter,
        },
    )
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["methodology_version"] == "1.1.0"
    assert snapshot["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    assert snapshot["ramsey_shelter_shadow"]["in_bugout_index"] is False
    assert snapshot["shelter_region_shadow"]["in_bugout_index"] is False
    assert snapshot["sf_shelter_shadow"]["in_bugout_index"] is False
    assert "ramsey_shelter_total_people" not in snapshot["metrics"]


def test_rendered_page_labels_each_companion_outside_the_score(tmp_path, monkeypatch):
    import runtime.publish.render as render

    snapshot = json.loads(LATEST.read_text())
    before = {key: snapshot[key] for key in SCORE_FIELDS}
    snapshot["ramsey_shelter_shadow"] = assemble_ramsey(
        {"ramsey_shelter_total_people": [{"date": "2026-08-01", "value": 480}]},
        [],
    )
    snapshot["shelter_region_shadow"] = fetch_region()
    snapshot["sf_shelter_shadow"] = assemble_sf(
        {"sf_shelter_occupancy_rate": [{"date": "2026-08-31", "value": 90.0}]},
        [],
    )
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)
    html = (tmp_path / "index.html").read_text()
    history = (tmp_path / "history.html").read_text()
    methodology = (tmp_path / "methodology.html").read_text()

    assert {key: snapshot[key] for key in SCORE_FIELDS} == before
    assert snapshot["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert snapshot["metrics"]["incident_rate"]["raw"] == 2723.0
    assert snapshot["metrics"]["trust_in_government"]["raw"] == 41.0
    for heading in (
        "Nashville–Davidson shelter checklist",
        "Austin/Travis County shelter checklist",
        "Ramsey County shelter census",
        "Denver shelter checklist",
        "San Francisco shelter occupancy",
    ):
        block = html.split(heading)[1].split("<div class=\"section-title\">")[0]
        assert "not in the BugOut Index" in block
        assert "No weight" in block or "no weight" in block
        assert "HUD AHAR" in block
        assert "Raw weight" not in block
    assert "Ramsey County only" in html
    assert "Nashville–Davidson only" in html
    assert "Austin/Travis County only" in html
    assert "Denver only" in html
    assert "not a U.S. total" in html
    assert "9mck-bcqu" in html
    assert "population_enrollees" in html
    assert "480" in html
    assert "2,907" in html
    assert "1,070" in html
    assert "93 %" in html
    assert "publication lag" in html.lower() or "Publication lag" in html or "lags" in html
    assert "San Francisco only" in html
    assert "occupancy rate, not a headcount" in html
    assert "kc49-udxn" in html
    assert "90.0 %" in html
    assert "not a U.S. total" in history
    assert "not a headcount" in history
    assert "9mck-bcqu" in methodology
    assert "not a headcount" in methodology
    assert "HUD AHAR" in methodology

    note = build_week_note(snapshot)
    text = " ".join(note)
    assert unexplained_numerals(note, snapshot) == []
    assert "Ramsey County shelter-census shadow series" in note[-1]
    assert "Nashville, Austin, and Denver shelter shadow series" in note[-1]
    assert "San Francisco shelter-occupancy shadow series" in note[-1]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "480" not in text
    assert "2907" not in text
    assert "2,907" not in text
    assert "1070" not in text
    assert "90.0" not in text
