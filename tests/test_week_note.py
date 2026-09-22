# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Week-note and tile-age copy is deterministic and sourced from the snapshot."""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from runtime.data.fetch.fetch_homelessness_rate import fetch as fetch_homelessness
from runtime.data.fetch.fetch_incident_rate import crime_file_provenance
from runtime.publish.week_note import (
    CORE_TITLES,
    MARKET_ORDER,
    PULSE_TITLES,
    build_week_note,
    describe_core_age,
    describe_pulse_age,
    format_index,
    unexplained_numerals,
)
from runtime.publish.weekly_run import build_snapshot, compute_index

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
CRIME_CSV = ROOT / "runtime" / "data" / "final_sample.csv"

PUBLISHED_RAWS = {
    "inflation_rate": 3.353016322755652,
    "incident_rate": 2723.0,
    "unemployment_rate": 4.1,
    "debt_to_gdp_ratio": 122.59387,
    "homelessness_rate": 0.23,
    "trust_in_government": 41.0,
}


def _days(publication: str, anchor: str) -> int:
    pub = date.fromisoformat(publication)
    start = date.fromisoformat(anchor)
    return (pub - start).days


def _inflation_move_snapshot() -> dict:
    """12 September 2026 versus 5 September: inflation and the index moved."""
    def core_row(when, index, inflation):
        return {
            "date": when,
            "bugout_index": index,
            "inflation_rate": inflation,
            "incident_rate": "2723.0",
            "unemployment_rate": "4.1",
            "debt_to_gdp_ratio": "122.59387",
            "homelessness_rate": "0.23",
            "trust_in_government": "41.0",
        }

    return {
        "publication_date": "2026-09-12",
        "bugout_index": 57.11,
        "metrics": {
            "inflation_rate": {"raw": 3.353016322755652, "source_fetched_at": "2026-08-01"},
            "incident_rate": {
                "raw": 2723.0,
                "source_fetched_at": None,
                "provenance": {
                    "kind": "file",
                    "value_month": "September 2024",
                    "value_month_end": "2024-09-30",
                    "file_through": "December 2024",
                    "file_updated": "2025-02-19",
                },
            },
            "unemployment_rate": {"raw": 4.1, "source_fetched_at": "2026-08-01"},
            "debt_to_gdp_ratio": {"raw": 122.59387, "source_fetched_at": "2026-01-01"},
            "homelessness_rate": {
                "raw": 0.23,
                "source_fetched_at": None,
                "provenance": {
                    "kind": "manual",
                    "last_set": "2024 HUD AHAR",
                    "observation_period": "January 2024 point-in-time count",
                    "reference_date": "2024-01-01",
                },
            },
            "trust_in_government": {
                "raw": 41.0,
                "source_fetched_at": "2025",
                "provenance": {"kind": "annual", "year": "2025"},
            },
        },
        "markets": {
            "fetched_at": "2026-09-12",
            "gold_usd_per_oz": 4349.7002,
            "silver_usd_per_oz": 64.622,
            "dxy": 118.0732,
        },
        "pulse": {
            "values": {
                "initial_jobless_claims": 206000.0,
                "consumer_sentiment_umich": 55.2,
                "business_confidence": 98.96989,
                "yield_curve_10y_2y": 0.33,
                "vix": 17.84,
            },
            "dates": {
                "initial_jobless_claims": "2026-09-05",
                "consumer_sentiment_umich": "2026-07-01",
                "business_confidence": "2024-01-01",
                "yield_curve_10y_2y": "2026-09-11",
                "vix": "2026-09-11",
            },
        },
        "history": {
            "bugout_index": [
                core_row("2026-09-05", "57.15", "3.303856050706308"),
                core_row("2026-09-12", "57.11", "3.353016322755652"),
            ],
            "markets": [
                {
                    "date": "2026-09-05",
                    "gold_usd_per_oz": "4431.1001",
                    "silver_usd_per_oz": "66.341",
                    "dxy": "118.7479",
                },
                {
                    "date": "2026-09-12",
                    "gold_usd_per_oz": "4349.7002",
                    "silver_usd_per_oz": "64.622",
                    "dxy": "118.0732",
                },
            ],
            "pulse": [
                {
                    "date": "2026-09-05",
                    "initial_jobless_claims": "206000.0",
                    "consumer_sentiment_umich": "55.2",
                    "business_confidence": "98.96989",
                    "yield_curve_10y_2y": "0.41",
                    "vix": "14.32",
                },
                {
                    "date": "2026-09-12",
                    "initial_jobless_claims": "206000.0",
                    "consumer_sentiment_umich": "55.2",
                    "business_confidence": "98.96989",
                    "yield_curve_10y_2y": "0.33",
                    "vix": "17.84",
                },
            ],
        },
    }


def test_published_inputs_still_score_57_11():
    results = {
        metric: {
            "status": "success",
            "fetched_at": None,
            "provenance": {"kind": "manual", "last_set": "ignored by scoring"},
            "data": {metric: raw},
        }
        for metric, raw in PUBLISHED_RAWS.items()
    }
    scored = compute_index(results)
    assert scored["index"] == 57.11
    snapshot = build_snapshot("2026-09-19", scored, results, {"status": "success", "data": {}}, {"data": {}, "dates": {}})
    assert snapshot["bugout_index"] == 57.11
    assert snapshot["metrics"]["inflation_rate"]["provenance"]["kind"] == "manual"
    assert snapshot["metrics"]["inflation_rate"]["raw"] == PUBLISHED_RAWS["inflation_rate"]


def test_fake_fetch_timestamp_is_not_shown():
    crime = describe_core_age(
        "incident_rate",
        {"raw": 2723.0, "source_fetched_at": "2025-01-01T00:00:00Z"},
        "2026-09-19",
    )
    homelessness = describe_core_age(
        "homelessness_rate",
        {"raw": 0.23, "source_fetched_at": "2025-01-01T00:00:00Z"},
        "2026-09-19",
    )
    assert "2025-01-01T00:00:00Z" not in crime["text"]
    assert crime["text"].startswith("file vintage")
    assert "2025-01-01T00:00:00Z" not in homelessness["text"]
    assert homelessness["text"].startswith("manual, last set")


def test_tile_ages_use_real_anchors():
    publication = "2026-09-19"
    inflation = describe_core_age(
        "inflation_rate",
        {"source_fetched_at": "2026-08-01"},
        publication,
    )
    assert inflation["text"] == f"observed 2026-08-01 · {_days(publication, '2026-08-01')} days old"
    assert inflation["stale"] is False

    crime = describe_core_age(
        "incident_rate",
        {
            "source_fetched_at": None,
            "provenance": {
                "kind": "file",
                "value_month": "September 2024",
                "value_month_end": "2024-09-30",
                "file_through": "December 2024",
                "file_updated": "2025-02-19",
            },
        },
        publication,
    )
    assert "September 2024" in crime["text"]
    assert "December 2024" in crime["text"]
    assert "2025-02-19" in crime["text"]
    assert f"{_days(publication, '2024-09-30')} days since 2024-09-30" in crime["text"]
    assert "2025-01-01" not in crime["text"]

    homelessness = describe_core_age(
        "homelessness_rate",
        {"provenance": fetch_homelessness()["provenance"]},
        publication,
    )
    assert homelessness["text"].startswith("manual, last set 2024 HUD AHAR")
    assert "January 2024 point-in-time count" in homelessness["text"]
    assert f"{_days(publication, '2024-01-01')} days since 2024-01-01" in homelessness["text"]

    trust = describe_core_age(
        "trust_in_government",
        {"source_fetched_at": "2025", "provenance": {"kind": "annual", "year": "2025"}},
        publication,
    )
    assert trust["text"].startswith("annual, last set 2025")
    assert f"{_days(publication, '2025-01-01')} days since 2025-01-01" in trust["text"]

    confidence = describe_pulse_age("2024-01-01", publication, flat=True)
    assert confidence["stale"] is True
    assert "stale" in confidence["text"]
    assert f"{_days(publication, '2024-01-01')} days old" in confidence["text"]
    assert "unchanged across recorded weeks" in confidence["text"]

    claims = describe_pulse_age("2026-09-12", publication, flat=False)
    assert claims["stale"] is False
    assert claims["text"] == f"observed 2026-09-12 · {_days(publication, '2026-09-12')} days old"
    spread = describe_pulse_age("2026-09-18", publication, flat=False)
    assert spread["text"] == "observed 2026-09-18 · 1 day old"


def test_crime_file_vintage_matches_the_committed_csv():
    dates = []
    updated = []
    with CRIME_CSV.open(newline="") as handle:
        for row in csv.DictReader(handle):
            dates.append(row["Date"])
            updated.append(row["Last Updated"])
    provenance = crime_file_provenance(dates, updated)
    assert provenance["kind"] == "file"
    assert provenance["value_month"] == "September 2024"
    assert provenance["value_month_end"] == "2024-09-30"
    assert provenance["file_through"] == "December 2024"
    assert provenance["file_updated"] == "2025-02-19"


def test_week_note_when_inflation_and_the_index_move():
    snapshot = _inflation_move_snapshot()
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == []
    assert "moved from 57.15 on 2026-09-05 to 57.11, a change of -0.04 points" in text
    assert "Inflation changed from 3.303856050706308 to 3.353016322755652" in text
    assert "observed 2026-08-01" in text
    unchanged = next(sentence for sentence in note if sentence.startswith("Unchanged core inputs"))
    for name in ("unemployment", "debt-to-GDP", "crime", "homelessness", "trust in government"):
        assert name in unchanged
    assert "manual, last set 2024 HUD AHAR" in unchanged
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "2025-01-01T00:00:00Z" not in text
    assert any("stale" in sentence for sentence in note)
    assert any("Gold changed" in sentence for sentence in note)
    assert any("VIX changed" in sentence for sentence in note)


def test_committed_snapshot_note_is_sourced():
    """The shipped snapshot produces a checkable note without locking next week's numbers."""
    snapshot = json.loads(LATEST.read_text())
    note = build_week_note(snapshot)
    text = " ".join(note)
    assert 4 <= len(note) <= 8
    assert unexplained_numerals(note, snapshot) == [], unexplained_numerals(note, snapshot)
    assert format_index(snapshot["bugout_index"]) in note[0]
    assert "not inputs to the BugOut Index score" in note[-1]
    assert "2025-01-01T00:00:00Z" not in text

    history = snapshot["history"]["bugout_index"]
    prior = history[-2]
    assert prior["date"] != snapshot["publication_date"]
    if format_index(prior["bugout_index"]) == format_index(snapshot["bugout_index"]):
        assert "unchanged" in note[0]
    else:
        assert "change of" in note[0]

    publication = snapshot["publication_date"]
    for key, entry in snapshot["metrics"].items():
        age = describe_core_age(key, entry, publication)
        assert age["text"]
        assert "2025-01-01T00:00:00Z" not in age["text"]
    assert describe_core_age("homelessness_rate", snapshot["metrics"]["homelessness_rate"], publication)["text"].startswith(
        "manual, last set"
    )
    assert "file vintage" in describe_core_age(
        "incident_rate", snapshot["metrics"]["incident_rate"], publication
    )["text"]
    confidence = describe_pulse_age(
        snapshot["pulse"]["dates"]["business_confidence"],
        publication,
        flat=True,
    )
    assert confidence["stale"] is True
    assert any("stale" in sentence for sentence in note)

    # A companion that actually moved is named. Markets and pulse stay outside the score.
    moved = []
    for key, title in list(PULSE_TITLES.items()):
        previous = snapshot["history"]["pulse"][-2][key]
        current = snapshot["pulse"]["values"][key]
        if float(previous) != float(current):
            moved.append(title.split()[-1].lower())
    for key, title in MARKET_ORDER:
        previous = snapshot["history"]["markets"][-2][key]
        current = snapshot["markets"][key]
        if float(previous) != float(current):
            moved.append(title)
    assert moved
    assert any(any(part in sentence.lower() for part in moved) for sentence in note)
    assert CORE_TITLES["inflation_rate"] in text.lower() or "Inflation" in text
