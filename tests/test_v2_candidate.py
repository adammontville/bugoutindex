# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""v2 candidate replay stays off the live score and matches its checked-in note."""
from __future__ import annotations

import csv
from pathlib import Path

from runtime.backtest.cli import main as v1_main
from runtime.backtest.harness import (
    OUTPUT_DIR,
    load_fixtures,
    load_published_raws,
    score_published_inputs,
)
from runtime.backtest.v2_candidate import (
    CANDIDATE_LABEL,
    COLUMNS,
    DATA_PULL_DATE,
    MONTHLY_NAME,
    NOTE_NAME,
    OUTPUT_DIR as V2_OUTPUT_DIR,
    PACKAGE_DIR,
    PUBLISHED_INCIDENT_RATE,
    SUMMARY_NAME,
    TRIAL_WEIGHTS,
    build_v2_rows,
    csv_fields,
    food_public_yoy,
    main,
    render_markdown,
    summarize,
)
from runtime.data.fetch.fetch_food_shadow import _public_yoy
from runtime.processing.formula import WEIGHTS
from runtime.processing.formula import compute_index as formula_compute_index
from runtime.publish.weekly_run import compute_index as weekly_compute_index

ROOT = Path(__file__).resolve().parents[1]


def _by_date(rows):
    return {row["date"]: row for row in rows}


def test_locked_score_and_live_path_are_untouched():
    raws = load_published_raws()
    assert score_published_inputs(raws)["index"] == 57.11
    payload = {metric: {"data": {metric: value}} for metric, value in raws.items()}
    assert formula_compute_index(payload)["index"] == 57.11
    assert weekly_compute_index(payload)["index"] == 57.11
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text(encoding="utf-8")
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    render = (ROOT / "runtime" / "publish" / "render.py").read_text(encoding="utf-8")
    latest = (ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "weekly-update.yml").read_text(encoding="utf-8")
    assert "v2_candidate" not in formula
    assert "v2_candidate" not in weekly
    assert "v2_candidate" not in render
    assert "v2_candidate" not in latest
    assert "runtime.backtest" not in weekly
    assert "v2_candidate" not in workflow
    assert "LNS12300060" not in formula
    assert "CPIUFDNS" not in formula
    assert "VIXCLS" not in formula
    assert sum(WEIGHTS.values()) == 0.72
    assert abs(sum(TRIAL_WEIGHTS.values()) - 1.0) < 1e-9
    assert set(TRIAL_WEIGHTS) != set(WEIGHTS)


def test_crisis_v1_columns_match_the_locked_replay():
    rows = _by_date(build_v2_rows())
    april = rows["2020-04-01"]
    assert april["v1_partial_index"] == 45.51
    assert april["v1_partial_band"] == "Low Stability"
    assert april["v1_held_index"] == 51.67
    assert april["v1_held_band"] == "Low Stability"
    assert april["v1_unemployment_rate"] == 14.8
    assert april["v1_level_source"] == "locked_fred_fixture_2026-09-23"
    assert april["methodology_reference"] == "1.0.0"
    assert april["candidate_label"] == CANDIDATE_LABEL
    october = rows["2009-10-01"]
    assert october["v1_unemployment_rate"] == 10.0
    assert october["v1_partial_band"] == "Moderate Stability"
    assert october["v2_incident_status"] == "excluded"
    assert october["v2_index"] == october["v2_without_crime_index"]


def test_august_2026_held_constant_is_still_57_11():
    august = _by_date(build_v2_rows())["2026-08-01"]
    assert august["v1_held_index"] == 57.11
    assert august["v1_held_band"] == "Moderate Stability"
    assert august["v1_level_source"] == "bls_pull_2026-09-26_plus_published_debt"
    assert august["v2_food_cpi_yoy"] == 2.7
    assert august["v2_prime_age_epop"] == 80.4
    assert august["v2_prime_age_lfpr"] == 83.4
    assert august["v2_incident_status"] == "excluded"
    assert august["v2_index"] == august["v2_without_crime_index"]
    assert august["v2_index"] != 57.11
    assert abs(august["v2_weight_denominator"] - 0.82) < 1e-9


def test_crime_trial_does_not_replace_the_lock_and_does_not_cover_2008():
    rows = build_v2_rows()
    assert all(row["v2_incident_rate"] != PUBLISHED_INCIDENT_RATE for row in rows)
    assert all(row["window"] != "2008" or row["v2_incident_status"] == "excluded" for row in rows)
    april = _by_date(rows)["2020-04-01"]
    assert april["v2_incident_status"] == "trial_observed"
    assert april["v2_incident_rate"] == 2642.84
    assert april["v2_incident_agencies"] == 621
    assert abs(april["v2_weight_denominator"] - 1.0) < 1e-9
    assert "incident_rate" in april["v2_inputs_present"]
    held = april["v2_if_crime_held_index"]
    assert held != april["v2_index"]
    assert PUBLISHED_INCIDENT_RATE == 2723.0


def test_october_2025_gap_is_not_filled_in():
    october = _by_date(build_v2_rows())["2025-10-01"]
    assert october["v2_inflation_rate"] is None
    assert october["v2_food_cpi_yoy"] is None
    assert october["v2_labor_utilization"] is None
    assert october["v1_unemployment_rate"] is None
    assert october["v2_inputs_present"] == "vix_month_mean|incident_rate"
    assert october["v1_debt_status"] == "observed"
    assert october["v1_partial_index"] != october["v2_index"]


def test_food_print_matches_the_shadow_fetcher():
    food = (PACKAGE_DIR / "fixtures" / "v2" / "CPIUFDNS.csv").read_text(encoding="utf-8")
    levels = {
        row.split(",")[0]: row.split(",")[1].strip()
        for row in food.splitlines()[1:]
    }
    assert food_public_yoy(levels["2026-08-01"], levels["2025-08-01"]) == _public_yoy(
        levels["2026-08-01"], levels["2025-08-01"]
    )
    assert food_public_yoy(levels["2026-08-01"], levels["2025-08-01"]) == 2.7


def test_bls_pull_matches_the_locked_fred_fixture_on_the_overlap():
    fixture = load_fixtures()
    bundle_cpi = {}
    with (PACKAGE_DIR / "fixtures" / "v2" / "CPIAUCSL.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bundle_cpi[row["observation_date"]] = float(row["CPIAUCSL"])
    bundle_un = {}
    with (PACKAGE_DIR / "fixtures" / "v2" / "LNS14000000.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bundle_un[row["observation_date"]] = float(row["LNS14000000"])
    overlap_cpi = set(fixture.cpi) & set(bundle_cpi)
    overlap_un = set(fixture.unemployment) & set(bundle_un)
    assert len(overlap_cpi) == len(fixture.cpi)
    assert len(overlap_un) == len(fixture.unemployment)
    assert all(abs(fixture.cpi[day] - bundle_cpi[day]) < 1e-9 for day in overlap_cpi)
    assert all(abs(fixture.unemployment[day] - bundle_un[day]) < 1e-9 for day in overlap_un)


def test_backtest_workflow_does_not_publish():
    text = (ROOT / ".github" / "workflows" / "backtest.yml").read_text(encoding="utf-8")
    assert "weekly_run" not in text
    assert "contents: read" in text
    assert "schedule:" not in text
    assert "test_v2_candidate.py" in text


def test_cli_prints_the_lock_and_writes_a_labeled_note(tmp_path, capsys):
    note = tmp_path / "note.md"
    code = main(["--check-locked", "--output", str(tmp_path), "--note", str(note)])
    assert code == 0
    printed = capsys.readouterr().out
    assert "2026-09-19 57.11 Moderate Stability methodology 1.0.0" in printed
    monthly = list(csv.DictReader((tmp_path / MONTHLY_NAME).open(encoding="utf-8")))
    assert monthly[0]["candidate_label"] == CANDIDATE_LABEL
    assert monthly[0]["data_pull_date"] == DATA_PULL_DATE
    assert "hypothesis" in note.read_text(encoding="utf-8").lower()
    assert "57.11" in note.read_text(encoding="utf-8")
    assert (tmp_path / SUMMARY_NAME).exists()
    # The v1 command is still the crisis replay and does not write the v2 note.
    v1_dir = tmp_path / "v1"
    assert v1_main(["--output", str(v1_dir), "--windows", "2020"]) == 0
    assert (v1_dir / "replay_partial.csv").exists()
    assert not (v1_dir / MONTHLY_NAME).exists()


def test_committed_v2_tables_match_the_harness():
    rows = build_v2_rows()
    fresh = [csv_fields(row) for row in rows]
    with (V2_OUTPUT_DIR / MONTHLY_NAME).open(newline="", encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert list(committed[0]) == list(COLUMNS)
    assert committed == fresh
    summary = summarize(rows)
    note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note == render_markdown(rows, summary)
    assert "October 2025" in note
    assert "45.62" in note
    assert "not a methodology version" in note.lower() or "not a methodology version" in note
    # v1 crisis CSVs are not rewritten by the v2 row builder.
    partial = (OUTPUT_DIR / "replay_partial.csv").read_text(encoding="utf-8")
    assert "2022-06-01" not in partial
    assert "v2_candidate" not in partial
