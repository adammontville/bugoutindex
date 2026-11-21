# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Crime refresh replay stays off the live score and matches its checked-in note."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.backtest.crime_live_replay import (
    CURRENT_RTCI_CSV,
    LATEST_PUBLICATION,
    LOCAL_RTCI_CSV,
    NOTE_NAME,
    PACKAGE_DIR,
    PUBLISHED_INCIDENT_RATE,
    SNAPSHOT_CANDIDATE_RATE,
    build_monthly_rows,
    build_publication_rows,
    load_vintages,
    main,
    rates_by_month,
    render_markdown,
    score_raws,
)
from runtime.backtest.harness import WEEKLY_CSV, load_published_raws, score_published_inputs
from runtime.processing.formula import METRIC_RANGES, WEIGHTS
from runtime.processing.formula import compute_index as formula_compute_index
from tests.snapshot_checks import assert_live_snapshot_matches_formula

ROOT = Path(__file__).resolve().parents[1]


def _by_date(rows):
    return {row["date"]: row for row in rows}


def test_live_publisher_files_stay_on_the_locked_score():
    raws = load_published_raws()
    assert raws["incident_rate"] == 2723.0
    assert score_published_inputs(raws)["index"] == 57.11
    assert PUBLISHED_INCIDENT_RATE == 2723.0
    assert METRIC_RANGES["incident_rate"] == (500, 8000)
    assert WEIGHTS["incident_rate"] == 0.12
    assert sum(WEIGHTS.values()) == 0.72
    # The live file is a later 1.1.1 publish. Its headline moves with FRED.
    # What stays is the methodology: schema 1, stamp 1.1.1, nationwide crime
    # rather than this replay's unweighted mean or the 2723 lock, and the
    # annual cells 0.22 and 39.
    latest = json.loads((ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert_live_snapshot_matches_formula(latest)
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text(encoding="utf-8")
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    assert "crime_live_replay" not in formula
    assert "crime_live_replay" not in weekly
    assert "schema_version" in weekly


def test_each_publication_keeps_its_locked_score_and_moves_only_crime():
    publications = list(csv.DictReader(WEEKLY_CSV.open(newline="", encoding="utf-8")))
    locked_weeks = [row for row in publications if row["date"] <= LATEST_PUBLICATION]
    rows = build_publication_rows()
    # The replay stops at the last 1.0.0 week. Later publishes are 1.1.x and
    # stay in the weekly file. Counting every row pinned the test to one Friday.
    assert LATEST_PUBLICATION == "2026-10-02"
    assert len(locked_weeks) == 25
    assert len(rows) == len(locked_weeks)
    assert locked_weeks[-1]["date"] == "2026-10-02"
    assert float(locked_weeks[-1]["incident_rate"]) == 2723.0
    assert float(locked_weeks[-1]["bugout_index"]) == 57.04
    assert [row["date"] for row in rows] == [row["date"] for row in locked_weeks]
    assert all(row["date"] <= LATEST_PUBLICATION for row in rows)

    # 2026-10-09 is the 1.1.0 unlock. Crime is the Nationwide Full Sample
    # 2443.27 (the population-weighted April 2026 rate on the checked-in RTCI
    # file), not the 1.0.0 lock 2723 and not this replay's unweighted 2074.97.
    # Homelessness and trust are still 0.23 and 41, so the published index
    # stays 57.66. 1.1.1 does not rewrite the row, and the replay does not
    # include it.
    unlock = next(row for row in publications if row["date"] == "2026-10-09")
    assert float(unlock["incident_rate"]) == 2443.27
    assert unlock["incident_rate_observation_date"] == "2026-04-30"
    assert float(unlock["homelessness_rate"]) == 0.23
    assert float(unlock["trust_in_government"]) == 41.0
    assert float(unlock["bugout_index"]) == 57.66
    assert "2026-10-09" not in {row["date"] for row in rows}

    # 2026-10-16 is the first 1.1.1 week: homelessness 0.22 (2025 AHAR) and
    # trust 39 (2026 Edelman). Crime stays off the 2723 lock. The exact
    # national rate can move when RTCI does, so later weeks are not pinned
    # to 2443.27.
    refreshed = [row for row in publications if row["date"] >= "2026-10-16"]
    assert refreshed
    for published in refreshed:
        assert float(published["homelessness_rate"]) == 0.22
        assert published["homelessness_rate_observation_date"] == "2025-01-01"
        assert float(published["trust_in_government"]) == 39.0
        assert published["trust_in_government_observation_date"] == "2026"
        assert float(published["incident_rate"]) != 2723.0
        assert published["date"] not in {row["date"] for row in rows}
    for published, row in zip(locked_weeks, rows):
        assert float(published["incident_rate"]) == 2723.0
        assert row["locked_index"] == float(published["bugout_index"])
        assert row["crime_value"] != 2723.0
        assert row["live_band"] == "Moderate Stability"
        assert row["locked_band"] == "Moderate Stability"
        assert row["lex_band"] == "Moderate Stability"
    by_date = _by_date(rows)
    assert by_date["2026-04-21"]["crime_value"] == 2146.38
    assert by_date["2026-04-21"]["rtci_month"] == "February 2026"
    assert by_date["2026-04-21"]["live_index"] == 58.31
    assert by_date["2026-04-25"]["crime_value"] == 2146.42
    assert by_date["2026-05-15"]["rtci_month"] == "February 2026"
    assert by_date["2026-05-22"]["crime_value"] == 2092.21
    assert by_date["2026-05-22"]["rtci_month"] == "March 2026"
    assert by_date["2026-05-22"]["agencies"] == 612
    assert by_date["2026-06-12"]["rtci_month"] == "March 2026"
    assert by_date["2026-06-19"]["crime_value"] == 2074.97
    assert by_date["2026-06-19"]["rtci_month"] == "April 2026"
    # These figures are the unweighted counterfactual on the 1.0.0 basket.
    # 1.1.0 scores the nationwide rate instead, and this replay does not.
    # 2074.97 -> 58.48 and 2234.66 -> 58.13 stay the right expectations.
    latest = by_date["2026-10-02"]
    assert latest["locked_index"] == 57.04
    assert latest["live_index"] == 58.48
    assert latest["live_difference"] == 1.44
    assert latest["crime_value"] == 2074.97
    assert latest["rtci_month"] == "April 2026"
    assert latest["agencies"] == 621
    assert latest["lex_crime_value"] == SNAPSHOT_CANDIDATE_RATE == 2234.66
    assert latest["lex_rtci_month"] == "September 2025"
    assert latest["lex_index"] == 58.13
    assert min(row["live_difference"] for row in rows) == 1.28
    assert max(row["live_difference"] for row in rows) == 1.44


def test_latest_basket_matches_compute_index_for_both_crime_values():
    published = list(csv.DictReader(WEEKLY_CSV.open(newline="", encoding="utf-8")))
    latest = next(row for row in published if row["date"] == "2026-10-02")
    base = {
        "inflation_rate": float(latest["inflation_rate"]),
        "incident_rate": 2723.0,
        "unemployment_rate": float(latest["unemployment_rate"]),
        "debt_to_gdp_ratio": float(latest["debt_to_gdp_ratio"]),
        "homelessness_rate": float(latest["homelessness_rate"]),
        "trust_in_government": float(latest["trust_in_government"]),
    }
    assert score_raws(base)["index"] == 57.04
    for crime, index in ((2074.97, 58.48), (2234.66, 58.13)):
        swapped = dict(base)
        swapped["incident_rate"] = crime
        scored = score_raws(swapped)
        direct = formula_compute_index(
            {metric: {"data": {metric: value}} for metric, value in swapped.items()}
        )
        assert scored["index"] == index
        assert scored["index"] == direct["index"]
        assert scored["band"] == "Moderate Stability"
        assert swapped["inflation_rate"] == base["inflation_rate"]
        assert swapped["unemployment_rate"] == base["unemployment_rate"]
        assert swapped["debt_to_gdp_ratio"] == base["debt_to_gdp_ratio"]
        assert swapped["homelessness_rate"] == base["homelessness_rate"]
        assert swapped["trust_in_government"] == base["trust_in_government"]


def test_monthly_current_file_matches_the_snapshot_diagnostics():
    rows = build_publication_rows()
    monthly = build_monthly_rows(rows)
    by_month = {row["rtci_month_start"]: row for row in monthly}
    september = by_month["2025-09-01"]
    april = by_month["2026-04-01"]
    old_month = by_month["2024-09-01"]
    assert september["crime_value"] == 2234.66
    assert september["score"] == 58.13
    assert september["difference"] == 1.09
    assert september["agencies"] == 621
    assert april["crime_value"] == 2074.97
    assert april["score"] == 58.48
    assert april["basket_publication"] == "2026-10-02"
    assert old_month["crime_value"] == 2481.82
    assert old_month["crime_value"] != 2723.0
    assert old_month["score"] == 57.58
    assert all(row["band"] == "Moderate Stability" for row in monthly)
    fixture = {
        row["observation_date"]: row
        for row in csv.DictReader(CURRENT_RTCI_CSV.open(newline="", encoding="utf-8"))
    }
    june = load_vintages()[-1]
    assert june["rtci_sha"].startswith("bc66ee94")
    assert june["unweighted"] == float(fixture["2026-04-01"]["incident_rate_unweighted"])
    assert june["population_weighted"] == float(fixture["2026-04-01"]["incident_rate_population_weighted"])
    assert june["lex_unweighted"] == float(fixture["2025-09-01"]["incident_rate_unweighted"])
    assert june["agencies"] == 621


def test_2723_is_the_local_file_text_sort_of_september_2024():
    summary = rates_by_month(LOCAL_RTCI_CSV)
    assert summary["file_updated"] == "2025-02-19"
    assert summary["lex_label"] == "September 2024"
    assert summary["lex"]["unweighted"] == 2723.0
    assert summary["lex"]["agencies"] == 399
    assert summary["calendar_label"] == "December 2024"
    assert summary["calendar"]["unweighted"] == 2654.48
    assert summary["calendar"]["agencies"] == 399
    assert {info["agencies"] for info in summary["by_label"].values()} == {399}


def test_checked_in_note_matches_the_replay():
    rows = build_publication_rows()
    monthly = build_monthly_rows(rows)
    note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note == render_markdown(rows, monthly)
    assert "| 2026-10-02 | 57.04 | 58.48 | +1.44 | 2074.97 | April 2026 | 621 |" in note
    assert "September 2025 at 2234.66" in note
    assert "scores **58.13**" in note
    assert "Pull request #78" in note
    assert "9a7594a" in note
    assert "1.28 to 1.44" in note


def test_cli_rewrites_the_note_without_touching_the_weekly_score(tmp_path):
    note = tmp_path / "CRIME_LIVE_REPLAY.md"
    assert main(["--output", str(tmp_path), "--note", str(note)]) == 0
    text = note.read_text(encoding="utf-8")
    assert text.startswith("# Crime input refresh replay")
    assert "57.04" in text
    publications = (tmp_path / "crime_live_publications.csv").read_text(encoding="utf-8")
    assert "2026-10-02,57.04," in publications
    assert "2723" not in publications
    weekly = WEEKLY_CSV.read_text(encoding="utf-8")
    assert "2723.0" in weekly
