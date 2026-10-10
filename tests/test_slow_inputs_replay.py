# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Slow-input replay stays off the live score and matches its checked-in note."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.backtest.harness import WEEKLY_CSV
from runtime.backtest.slow_inputs_replay import (
    BASKET_DATE,
    EDELMAN_REFRESH,
    HUD_REFRESH,
    NOTE_NAME,
    PACKAGE_DIR,
    basket_extras,
    build_publication_rows,
    main,
    render_markdown,
    score_raws,
)
from runtime.processing.formula import CORE_METRICS, compute_index

ROOT = Path(__file__).resolve().parents[1]


def _by_date(rows):
    return {row["date"]: row for row in rows}


def test_live_files_keep_the_checklist_and_the_formula_ignores_the_replay():
    latest = json.loads((ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["methodology_version"] == "1.1.0"
    assert latest["bugout_index"] == 57.66
    assert latest["publication_date"] == BASKET_DATE
    assert latest["metrics"]["homelessness_rate"]["raw"] == 0.23
    assert latest["metrics"]["homelessness_rate"]["observation_date"] == "2024-01-01"
    assert latest["metrics"]["trust_in_government"]["raw"] == 41.0
    assert latest["metrics"]["trust_in_government"]["observation_date"] == "2025"
    checklist = (ROOT / "runtime" / "data" / "annual_inputs.csv").read_text(encoding="utf-8")
    assert "homelessness_rate,0.23," in checklist
    assert "trust_in_government,41," in checklist
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text(encoding="utf-8")
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    assert "slow_inputs_replay" not in formula
    assert "slow_inputs_replay" not in weekly
    for companion in ("nyc_dhs", "pew_public_trust", "gallup_congress"):
        assert companion not in CORE_METRICS


def test_each_week_matches_the_published_score_until_a_slot_is_substituted():
    publications = list(csv.DictReader(WEEKLY_CSV.open(newline="", encoding="utf-8")))
    rows = build_publication_rows()
    assert len(rows) == len(publications) == 26
    assert [row["date"] for row in rows] == [row["date"] for row in publications]
    for published, row in zip(publications, rows):
        assert row["published_index"] == float(published["bugout_index"])
        assert float(published["homelessness_rate"]) == 0.23
        assert float(published["trust_in_government"]) == 41.0
        assert row["published_band"] == "Moderate Stability"
        assert row["same_band"] == "Moderate Stability"
        assert row["pew_band"] == "Low Stability"
        assert row["pew_value"] == 17.0
        assert row["edelman_value"] == EDELMAN_REFRESH
    by_date = _by_date(rows)
    early = by_date["2026-05-22"]
    assert early["hud_value"] == 0.23
    assert early["hud_difference"] == 0.0
    switched = by_date["2026-05-29"]
    assert switched["hud_value"] == HUD_REFRESH == 0.22
    assert switched["hud_difference"] == 0.25
    assert by_date["2026-07-10"]["gallup_held_published"] is True
    assert by_date["2026-07-10"]["gallup_index"] == by_date["2026-07-10"]["published_index"]
    assert by_date["2026-07-17"]["gallup_held_published"] is False
    assert by_date["2026-07-17"]["gallup_value"] == 27.0
    assert by_date["2026-07-17"]["gallup_band"] == "Low Stability"
    basket = by_date[BASKET_DATE]
    assert basket["published_index"] == 57.66
    assert basket["hud_index"] == 57.91
    assert basket["edelman_index"] == 57.25
    assert basket["same_index"] == 57.50
    assert basket["same_difference"] == -0.16
    assert basket["pew_index"] == 52.66
    assert basket["gallup_index"] == 54.75
    assert all(row["same_band"] == "Moderate Stability" for row in rows)
    assert min(row["same_difference"] for row in rows) == -0.42
    assert max(row["same_difference"] for row in rows) == -0.16


def test_basket_matches_compute_index_for_each_substitution():
    published = list(csv.DictReader(WEEKLY_CSV.open(newline="", encoding="utf-8")))
    latest = next(row for row in published if row["date"] == BASKET_DATE)
    base = {metric: float(latest[metric]) for metric in CORE_METRICS}
    assert score_raws(base)["index"] == 57.66
    cases = {
        (0.22, 41.0): 57.91,
        (0.23, 39.0): 57.25,
        (0.22, 39.0): 57.50,
        (0.23, 17.0): 52.66,
        (0.23, 27.0): 54.75,
        (0.23, 9.0): 51.00,
        (0.5, 41.0): 50.91,
    }
    for (homelessness, trust), index in cases.items():
        swapped = dict(base)
        swapped["homelessness_rate"] = homelessness
        swapped["trust_in_government"] = trust
        scored = score_raws(swapped)
        direct = compute_index(
            {metric: {"data": {metric: value}} for metric, value in swapped.items()}
        )
        assert scored["index"] == index
        assert scored["index"] == direct["index"]
        assert swapped["inflation_rate"] == base["inflation_rate"]
        assert swapped["incident_rate"] == base["incident_rate"]
        assert swapped["unemployment_rate"] == base["unemployment_rate"]
        assert swapped["debt_to_gdp_ratio"] == base["debt_to_gdp_ratio"]
    extras = basket_extras()
    assert extras["congress_index"] == 51.00
    assert extras["clamped_index"] == 50.91
    assert extras["congress_band"] == "Low Stability"
    assert extras["clamped_band"] == "Low Stability"


def test_checked_in_note_matches_the_replay():
    rows = build_publication_rows()
    note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note == render_markdown(rows, basket_extras())
    assert "| 2026-10-09 | 57.66 | 57.91 | 57.25 | 57.50 | 52.66 | 54.75 |" in note
    assert "0.22" in note
    assert "**39**" in note
    assert "Low Stability" in note
    assert "slow_inputs_replay" not in (
        ROOT / "runtime" / "processing" / "formula.py"
    ).read_text(encoding="utf-8")


def test_cli_rewrites_the_note_without_touching_the_weekly_score(tmp_path):
    note = tmp_path / "SLOW_INPUTS_REPLAY.md"
    before = WEEKLY_CSV.read_text(encoding="utf-8")
    assert main(["--output", str(tmp_path), "--note", str(note)]) == 0
    text = note.read_text(encoding="utf-8")
    assert text.startswith("# Slow-input refresh replay")
    assert "57.50" in text
    publications = (tmp_path / "slow_inputs_publications.csv").read_text(encoding="utf-8")
    assert "2026-10-09,57.66," in publications
    assert WEEKLY_CSV.read_text(encoding="utf-8") == before
