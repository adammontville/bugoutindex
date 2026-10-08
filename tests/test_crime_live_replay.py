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
    latest = json.loads((ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["schema_version"] == 1
    assert latest["methodology_version"] == "1.0.0"
    assert latest["bugout_index"] == 57.04
    assert latest["publication_date"] == "2026-10-02"
    crime = latest["metrics"]["incident_rate"]
    assert crime["raw"] == 2723.0
    assert crime["observation_date"] is None
    assert crime["provenance"]["value_month"] == "April 2026"
    assert crime["provenance"]["value_month_end"] == "2026-04-30"
    assert crime["provenance"]["file_through"] == "April 2026"
    assert crime["diagnostics"]["candidate_incident_rate"] == 2074.97
    assert crime["diagnostics"]["candidate_month"] == "April 2026"
    assert crime["diagnostics"]["population_weighted_incident_rate"] == 2443.27
    assert crime["diagnostics"]["latest_month_incident_rate"] == 2074.97
    assert crime["diagnostics"]["latest_month"] == "April 2026"
    assert crime["diagnostics"]["index_input"] is False
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text(encoding="utf-8")
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    assert "crime_live_replay" not in formula
    assert "crime_live_replay" not in weekly
    assert "schema_version" in weekly


def test_each_publication_keeps_its_locked_score_and_moves_only_crime():
    publications = list(csv.DictReader(WEEKLY_CSV.open(newline="", encoding="utf-8")))
    rows = build_publication_rows()
    assert len(rows) == len(publications) == 25
    assert [row["date"] for row in rows] == [row["date"] for row in publications]
    for published, row in zip(publications, rows):
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
