# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Observation dates sit beside raw values and make a same-date revision visible."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.data.fetch.fetch_homelessness_rate import fetch as fetch_homelessness
from runtime.data.fetch.fetch_incident_rate import fetch as fetch_crime
from runtime.data.fetch.fetch_trust_in_government import fetch as fetch_trust
from runtime.processing.formula import CORE_METRICS
from runtime.publish.observation_dates import (
    NEW_PERIOD,
    REVISION,
    UNDATED_CHANGE,
    UNCHANGED,
    apply_known_dates,
    classify_core_change,
    ensure_csv_schema,
    observation_column,
    observation_date_for,
    weekly_boi_headers,
)
from runtime.publish.week_note import build_week_note, describe_core_age, unexplained_numerals
from runtime.publish.weekly_run import (
    build_snapshot,
    compute_index,
    core_history_row,
    load_history,
)

ROOT = Path(__file__).resolve().parents[1]
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
LATEST = ROOT / "docs" / "data" / "latest.json"

PUBLISHED_RAWS = {
    "inflation_rate": 3.353016322755652,
    "incident_rate": 2723.0,
    "unemployment_rate": 4.1,
    "debt_to_gdp_ratio": 122.59387,
    "homelessness_rate": 0.23,
    "trust_in_government": 41.0,
}


def _rows() -> list:
    with WEEKLY_CSV.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _by_date() -> dict:
    return {row["date"]: row for row in _rows()}


def _note_shell(**overrides) -> dict:
    """Minimal snapshot. Callers override metrics, history, and the index."""
    snapshot = {
        "publication_date": "2026-06-26",
        "bugout_index": 56.30,
        "metrics": {},
        "markets": {"fetched_at": "2026-06-26", "gold_usd_per_oz": 1, "silver_usd_per_oz": 1, "dxy": 1},
        "pulse": {
            "values": {
                "initial_jobless_claims": 1,
                "consumer_sentiment_umich": 1,
                "business_confidence": 1,
                "yield_curve_10y_2y": 1,
                "vix": 1,
            },
            "dates": {
                "initial_jobless_claims": "2026-06-20",
                "consumer_sentiment_umich": "2026-06-01",
                "business_confidence": "2026-06-01",
                "yield_curve_10y_2y": "2026-06-26",
                "vix": "2026-06-25",
            },
        },
        "history": {"bugout_index": [], "markets": [], "pulse": []},
    }
    snapshot.update(overrides)
    return snapshot


def _core(raw, observed, **extra):
    entry = {"raw": raw, "observation_date": observed, "source_fetched_at": observed}
    entry.update(extra)
    return entry


def test_observation_dates_are_not_score_inputs():
    plain = {metric: {"data": {metric: raw}} for metric, raw in PUBLISHED_RAWS.items()}
    dated = {
        metric: {
            "data": {metric: raw},
            "observation_date": "2020-01-01",
            "fetched_at": "1999-01-01",
            "provenance": {"kind": "manual", "reference_date": "1990-01-01"},
        }
        for metric, raw in PUBLISHED_RAWS.items()
    }
    assert compute_index(plain)["index"] == 57.11
    assert compute_index(dated) == compute_index(plain)


def test_new_publish_records_observation_dates_beside_raw_values():
    payloads = {
        "inflation_rate": {"fetched_at": "2026-08-01", "observation_date": "2026-08-01", "data": {"inflation_rate": PUBLISHED_RAWS["inflation_rate"]}},
        "incident_rate": {
            "fetched_at": None,
            "observation_date": "2024-09-30",
            "provenance": {"kind": "file", "value_month_end": "2024-09-30"},
            "data": {"incident_rate": 2723.0},
        },
        "unemployment_rate": {"fetched_at": "2026-08-01", "observation_date": "2026-08-01", "data": {"unemployment_rate": 4.1}},
        "debt_to_gdp_ratio": {"fetched_at": "2026-01-01", "observation_date": "2026-01-01", "data": {"debt_to_gdp_ratio": 122.59387}},
        "homelessness_rate": {
            "fetched_at": None,
            "observation_date": "2024-01-01",
            "provenance": {"kind": "manual", "reference_date": "2024-01-01"},
            "data": {"homelessness_rate": 0.23},
        },
        "trust_in_government": {
            "fetched_at": "2025",
            "observation_date": "2025",
            "provenance": {"kind": "annual", "year": "2025"},
            "data": {"trust_in_government": 41.0},
        },
    }
    scored = compute_index(payloads)
    assert scored["index"] == 57.11
    snapshot = build_snapshot("2026-09-19", scored, payloads, {"status": "success", "data": {}}, {"data": {}, "dates": {}})
    row = core_history_row("2026-09-19", scored, payloads)
    assert set(weekly_boi_headers()) == set(row)
    for metric, expected in {
        "inflation_rate": "2026-08-01",
        "incident_rate": "2024-09-30",
        "unemployment_rate": "2026-08-01",
        "debt_to_gdp_ratio": "2026-01-01",
        "homelessness_rate": "2024-01-01",
        "trust_in_government": "2025",
    }.items():
        assert snapshot["metrics"][metric]["observation_date"] == expected
        assert snapshot["metrics"][metric]["raw"] == PUBLISHED_RAWS[metric]
        assert row[observation_column(metric)] == expected
        assert row[metric] == PUBLISHED_RAWS[metric]


def test_placeholder_timestamp_is_not_an_observation_date():
    payload = {"fetched_at": "2025-01-01T00:00:00Z", "source_fetched_at": "2025-01-01T00:00:00Z", "data": {"incident_rate": 2723.0}}
    assert observation_date_for("incident_rate", payload) is None
    dated = dict(payload, provenance={"kind": "file", "value_month_end": "2024-09-30"})
    assert observation_date_for("incident_rate", dated) == "2024-09-30"


def test_classify_same_date_revision_versus_new_period():
    assert classify_core_change(122.77209, 122.59387, "2026-01-01", "2026-01-01") == REVISION
    assert classify_core_change(122.56815, 122.77209, "2025-10-01", "2026-01-01") == NEW_PERIOD
    assert classify_core_change(4.3, 4.3, "2026-05-01", "2026-05-01") == UNCHANGED
    assert classify_core_change(122.57, 122.59, "", "2026-01-01") == UNDATED_CHANGE
    assert classify_core_change(122.57, 122.59, None, None) == UNDATED_CHANGE


def test_week_note_labels_a_same_date_fred_revision():
    """Debt changes, unemployment does not, and both keep their observation dates."""
    prior = {
        "date": "2026-06-19",
        "bugout_index": "56.28",
        "inflation_rate": "4.166614684049648",
        "inflation_rate_observation_date": "2026-05-01",
        "incident_rate": "2723.0",
        "incident_rate_observation_date": None,
        "unemployment_rate": "4.3",
        "unemployment_rate_observation_date": "2026-05-01",
        "debt_to_gdp_ratio": "122.77209",
        "debt_to_gdp_ratio_observation_date": "2026-01-01",
        "homelessness_rate": "0.23",
        "homelessness_rate_observation_date": None,
        "trust_in_government": "41.0",
        "trust_in_government_observation_date": "2025",
    }
    current_date = "2026-06-26"
    snapshot = _note_shell(
        publication_date=current_date,
        bugout_index=56.30,
        metrics={
            "inflation_rate": _core(4.166614684049648, "2026-05-01"),
            "incident_rate": _core(2723.0, None),
            "unemployment_rate": _core(4.3, "2026-05-01"),
            "debt_to_gdp_ratio": _core(122.59387, "2026-01-01"),
            "homelessness_rate": _core(0.23, None),
            "trust_in_government": _core(41.0, "2025"),
        },
    )
    snapshot["history"]["bugout_index"] = [prior, {**prior, "date": current_date, "bugout_index": "56.30", "debt_to_gdp_ratio": "122.59387"}]
    snapshot["history"]["markets"] = [{"date": "2026-06-19", "gold_usd_per_oz": "1", "silver_usd_per_oz": "1", "dxy": "1"}]
    snapshot["history"]["pulse"] = [{
        "date": "2026-06-19",
        "initial_jobless_claims": "1",
        "consumer_sentiment_umich": "1",
        "business_confidence": "1",
        "yield_curve_10y_2y": "1",
        "vix": "1",
    }]
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert unexplained_numerals(note, snapshot) == []
    assert "Debt-to-GDP was revised from 122.77209 to 122.59387 for the same observation date 2026-01-01" in text
    assert "unemployment" in text.lower()
    assert "unemployment was revised" not in text.lower()
    assert "revised" in text.lower()


def test_week_note_labels_a_new_observation_period_without_calling_it_a_revision():
    prior = {
        "date": "2026-06-05",
        "bugout_index": "56.62",
        "unemployment_rate": "4.3",
        "unemployment_rate_observation_date": "2026-05-01",
        "debt_to_gdp_ratio": "122.56815",
        "debt_to_gdp_ratio_observation_date": "2025-10-01",
        "inflation_rate": "3.0",
        "inflation_rate_observation_date": "2026-04-01",
        "incident_rate": "2723.0",
        "homelessness_rate": "0.23",
        "trust_in_government": "41.0",
        "trust_in_government_observation_date": "2025",
    }
    snapshot = _note_shell(
        publication_date="2026-06-12",
        bugout_index=56.30,
        metrics={
            "inflation_rate": _core(3.0, "2026-04-01"),
            "incident_rate": _core(2723.0, None),
            "unemployment_rate": _core(4.2, "2026-06-01"),
            "debt_to_gdp_ratio": _core(122.77209, "2026-01-01"),
            "homelessness_rate": _core(0.23, None),
            "trust_in_government": _core(41.0, "2025"),
        },
    )
    snapshot["history"]["bugout_index"] = [prior]
    snapshot["history"]["markets"] = [{"date": "2026-06-05", "gold_usd_per_oz": "1", "silver_usd_per_oz": "1", "dxy": "1"}]
    snapshot["history"]["pulse"] = [{
        "date": "2026-06-05",
        "initial_jobless_claims": "1",
        "consumer_sentiment_umich": "1",
        "business_confidence": "1",
        "yield_curve_10y_2y": "1",
        "vix": "1",
    }]
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert unexplained_numerals(note, snapshot) == []
    assert "was revised" not in text
    assert "Unemployment changed from 4.3 (observed 2026-05-01) to 4.2 (observed 2026-06-01)" in text
    assert "debt-to-GDP changed from 122.56815 (observed 2025-10-01) to 122.77209 (observed 2026-01-01)" in text


def test_tile_age_prefers_observation_date_over_fetched_at():
    age = describe_core_age(
        "inflation_rate",
        {"source_fetched_at": "2020-01-01", "observation_date": "2026-08-01"},
        "2026-09-19",
    )
    assert age["text"].startswith("observed 2026-08-01")
    assert "2020-01-01" not in age["text"]


def test_manual_fetchers_keep_published_raws_and_record_periods():
    homelessness = fetch_homelessness()
    assert homelessness["data"]["homelessness_rate"] == 0.23
    assert homelessness["fetched_at"] is None
    assert homelessness["observation_date"] == "2024-01-01"

    trust = fetch_trust()
    assert trust["data"]["trust_in_government"] == 41.0
    assert trust["observation_date"] == "2025"

    crime = fetch_crime()
    assert crime["data"]["incident_rate"] == 2723.0
    assert crime["fetched_at"] is None
    assert crime["observation_date"] == "2024-09-30"


def test_schema_upgrade_leaves_old_dates_blank(tmp_path):
    path = tmp_path / "weekly_bugout_index.csv"
    path.write_bytes(
        b"date,bugout_index,inflation_rate,incident_rate,unemployment_rate,debt_to_gdp_ratio,homelessness_rate,trust_in_government,inflation_rate_normalized,incident_rate_normalized,unemployment_rate_normalized,debt_to_gdp_ratio_normalized,homelessness_rate_normalized,trust_in_government_normalized\r\n"
        b"2026-06-19,56.28,4.166614684049648,2723.0,4.3,122.77209,0.23,41.0,43.33,70.36,82.8,38.61,54.0,51.25\r\n"
    )
    assert ensure_csv_schema(path) is True
    assert ensure_csv_schema(path) is False
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == weekly_boi_headers()
        row = next(reader)
    assert row["debt_to_gdp_ratio"] == "122.77209"
    assert row["incident_rate"] == "2723.0"
    assert row["homelessness_rate"] == "0.23"
    assert row["trust_in_government"] == "41.0"
    for metric in CORE_METRICS:
        assert row[observation_column(metric)] == ""


def test_apply_known_dates_requires_a_matching_raw_and_rejects_placeholders():
    rows = [{
        "date": "2026-06-19",
        "bugout_index": "56.28",
        "inflation_rate": "1",
        "incident_rate": "2723.0",
        "unemployment_rate": "4.3",
        "debt_to_gdp_ratio": "122.77209",
        "homelessness_rate": "0.23",
        "trust_in_government": "41.0",
    }]
    snapshots = {
        "2026-06-19": {
            "inflation_rate": {"raw": 9.9, "source_fetched_at": "2026-05-01"},
            "incident_rate": {"raw": 2723.0, "source_fetched_at": "2025-01-01T00:00:00Z"},
            "unemployment_rate": {"raw": 4.3, "source_fetched_at": "2026-05-01"},
            "debt_to_gdp_ratio": {"raw": 122.77209, "source_fetched_at": "2026-01-01"},
            "homelessness_rate": {"raw": 0.23, "source_fetched_at": "2025-01-01T00:00:00Z"},
            "trust_in_government": {"raw": 41.0, "source_fetched_at": "2025"},
        }
    }
    filled = apply_known_dates(rows, snapshots)
    assert filled[0]["inflation_rate"] == "1"
    assert filled[0]["inflation_rate_observation_date"] == ""
    assert filled[0]["incident_rate_observation_date"] == ""
    assert filled[0]["homelessness_rate_observation_date"] == ""
    assert filled[0]["unemployment_rate_observation_date"] == "2026-05-01"
    assert filled[0]["debt_to_gdp_ratio_observation_date"] == "2026-01-01"
    assert filled[0]["trust_in_government_observation_date"] == "2025"
    assert filled[0]["debt_to_gdp_ratio"] == "122.77209"

    again = apply_known_dates(filled, {
        "2026-06-19": {"debt_to_gdp_ratio": {"raw": 122.77209, "source_fetched_at": "1999-01-01"}}
    })
    assert again[0]["debt_to_gdp_ratio_observation_date"] == "2026-01-01"


def test_committed_history_keeps_the_june_revision_and_does_not_invent_crime_dates():
    rows = _by_date()
    with WEEKLY_CSV.open(newline="") as handle:
        assert csv.DictReader(handle).fieldnames == weekly_boi_headers()

    june_12 = rows["2026-06-12"]
    june_19 = rows["2026-06-19"]
    june_26 = rows["2026-06-26"]
    published = rows["2026-09-19"]

    assert float(published["bugout_index"]) == 57.11
    assert float(published["incident_rate"]) == 2723.0
    assert float(published["homelessness_rate"]) == 0.23
    assert float(published["trust_in_government"]) == 41.0
    assert published["incident_rate_observation_date"] == "2024-09-30"
    assert published["homelessness_rate_observation_date"] == "2024-01-01"
    assert published["debt_to_gdp_ratio_observation_date"] == "2026-01-01"

    assert june_12["debt_to_gdp_ratio_observation_date"] == "2025-10-01"
    assert june_19["debt_to_gdp_ratio_observation_date"] == "2026-01-01"
    assert june_26["debt_to_gdp_ratio_observation_date"] == "2026-01-01"
    assert classify_core_change(
        june_12["debt_to_gdp_ratio"],
        june_19["debt_to_gdp_ratio"],
        june_12["debt_to_gdp_ratio_observation_date"],
        june_19["debt_to_gdp_ratio_observation_date"],
    ) == NEW_PERIOD
    assert classify_core_change(
        june_19["debt_to_gdp_ratio"],
        june_26["debt_to_gdp_ratio"],
        june_19["debt_to_gdp_ratio_observation_date"],
        june_26["debt_to_gdp_ratio_observation_date"],
    ) == REVISION

    for when, row in rows.items():
        assert "2025-01-01T00:00:00Z" not in "".join(row.values())
        if when != "2026-09-19":
            assert row["incident_rate_observation_date"] == ""
            assert row["homelessness_rate_observation_date"] == ""
        for metric in ("inflation_rate", "unemployment_rate", "debt_to_gdp_ratio", "trust_in_government"):
            assert row[observation_column(metric)]

    latest = json.loads(LATEST.read_text())
    assert latest["bugout_index"] == 57.11
    assert latest["methodology_version"] == "1.0.0"
    history = load_history(WEEKLY_CSV, limit=100)
    assert latest["history"]["bugout_index"] == history
    published_history = next(row for row in history if row["date"] == "2026-09-19")
    for metric in CORE_METRICS:
        assert latest["metrics"][metric]["observation_date"] == published_history[observation_column(metric)]
        assert float(latest["metrics"][metric]["raw"]) == float(published[metric])
    assert latest["metrics"]["incident_rate"]["raw"] == 2723.0
    assert latest["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert latest["metrics"]["trust_in_government"]["raw"] == 41.0
