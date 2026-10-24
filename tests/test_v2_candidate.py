# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""v2 basket replay stays off the live score and matches its checked-in note."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.backtest.cli import main as v1_main
from runtime.backtest.harness import (
    OUTPUT_DIR,
    load_fixtures,
    load_published_raws,
    parse_series_csv,
    score_published_inputs,
)
from runtime.backtest.v2_candidate import (
    ADDON_WEIGHT,
    BASKET_ADDONS,
    CANDIDATE_LABEL,
    CHART_NAME,
    COLUMNS,
    MONTHLY_NAME,
    NOTE_NAME,
    OUTPUT_DIR as V2_OUTPUT_DIR,
    PACKAGE_DIR,
    RANGES,
    SUMMARY_NAME,
    WEEKLY_NAME,
    build_v2_rows,
    csv_fields,
    current_reading,
    food_public_yoy,
    main,
    weekly_volatility,
    write_outputs,
)
from runtime.data.fetch.fetch_food_shadow import _public_yoy
from runtime.processing.formula import CORE_METRICS, METRIC_RANGES, WEIGHTS
from runtime.processing.formula import compute_index as formula_compute_index
from runtime.publish.weekly_run import compute_index as weekly_compute_index

ROOT = Path(__file__).resolve().parents[1]
LIVE_PATHS = (
    ROOT / "runtime" / "processing" / "formula.py",
    ROOT / "runtime" / "publish" / "weekly_run.py",
    ROOT / "runtime" / "publish" / "render.py",
    ROOT / "runtime" / "publish" / "snapshot_schema.py",
    ROOT / "docs" / "data" / "latest.json",
    ROOT / "runtime" / "data" / "weekly_bugout_index.csv",
    ROOT / ".github" / "workflows" / "weekly-update.yml",
)
# Series the live site already shows as shadows or pulse. They must stay
# out of the scored formula. The basket-only series must stay out of the
# publisher entirely.
SHADOW_SERIES = ("LNS12300060", "CPIUFDNS", "VIXCLS")
BASKET_ONLY_MARKERS = ("v2_candidate", "NFCICREDIT", "B25070", "DRSFRMACBS")


def _by_date(rows):
    return {row["date"]: row for row in rows}


def _payload(raws):
    return {metric: {"data": {metric: value}} for metric, value in raws.items()}


def test_locked_score_and_live_path_are_untouched():
    raws = load_published_raws()
    assert score_published_inputs(raws)["index"] == 57.11
    assert formula_compute_index(_payload(raws))["index"] == 57.11
    assert weekly_compute_index(_payload(raws))["index"] == 57.11
    latest = json.loads((ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["methodology_version"] == "1.1.0"
    assert latest["bugout_index"] == 57.66
    published = {metric: float(latest["metrics"][metric]["raw"]) for metric in CORE_METRICS}
    assert formula_compute_index(_payload(published))["index"] == 57.66
    schema = (ROOT / "runtime" / "publish" / "snapshot_schema.py").read_text(encoding="utf-8")
    assert 'METHODOLOGY_VERSION = "1.1.1"' in schema
    formula = (ROOT / "runtime" / "processing" / "formula.py").read_text(encoding="utf-8")
    for marker in SHADOW_SERIES + BASKET_ONLY_MARKERS:
        assert marker not in formula, marker
    for path in LIVE_PATHS:
        text = path.read_text(encoding="utf-8")
        for marker in BASKET_ONLY_MARKERS:
            assert marker not in text, f"{marker} in {path.name}"
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    assert "runtime.backtest" not in weekly
    assert sum(WEIGHTS.values()) == 0.72
    assert ADDON_WEIGHT == 0.08
    addon_names = {name for names in BASKET_ADDONS.values() for name in names}
    assert addon_names.isdisjoint(WEIGHTS)
    for metric in CORE_METRICS:
        assert RANGES[metric] == METRIC_RANGES[metric]
    joined = " ".join(addon_names)
    assert "pew" not in joined and "gallup" not in joined and "shelter" not in joined


def test_april_2020_keeps_the_locked_partial_and_uses_nationwide_crime():
    april = _by_date(build_v2_rows())["2020-04-01"]
    assert april["methodology_reference"] == "1.1.1"
    assert april["candidate_label"] == CANDIDATE_LABEL
    assert april["v1_partial_index"] == 45.51
    assert april["v1_partial_band"] == "Low Stability"
    assert april["v1_100_held_index"] == 51.67
    assert april["v1_100_held_band"] == "Low Stability"
    assert april["v1_111_band"] == "Low Stability"
    assert april["v1_111_index"] != 51.67
    assert april["unemployment_rate"] == 14.8
    assert april["incident_status"] == "observed"
    assert april["incident_rate"] == 2955.84
    assert april["incident_unweighted"] == 2642.84
    assert april["incident_rate"] != 2723
    assert april["incident_agencies"] == 621
    assert "incident_rate" in april["v1_111_inputs_present"]
    assert april["b_index"] > april["v1_111_index"]
    assert april["a_index"] < april["v1_111_index"]


def test_august_2026_held_constant_is_still_57_11():
    august = _by_date(build_v2_rows())["2026-08-01"]
    assert august["v1_100_held_index"] == 57.11
    assert august["v1_100_held_band"] == "Moderate Stability"
    assert august["v1_111_band"] == "Moderate Stability"
    assert august["v1_111_index"] != 57.11
    assert august["incident_status"] == "carried_forward"
    assert august["incident_rate"] == 2443.27
    assert august["incident_observation_date"] == "2026-04-01"
    assert august["incident_unweighted"] == 2074.97
    assert august["food_cpi_yoy"] == 2.7
    assert august["prime_age_epop"] == 80.4
    assert abs(august["a_denominator"] - 0.88) < 1e-9
    assert abs(august["b_denominator"] - 0.96) < 1e-9
    assert abs(august["c_denominator"] - 0.88) < 1e-9


def test_pre_2018_crime_is_excluded_and_2022_v1_is_low():
    rows = build_v2_rows()
    assert all(
        row["incident_status"] == "excluded"
        for row in rows
        if row["window"] == "2008"
    )
    october = _by_date(rows)["2008-10-01"]
    assert october["c_index"] < october["v1_111_index"]
    assert october["c_band"] == "Low Stability"
    year_2022 = [row for row in rows if row["window"] == "2022"]
    assert year_2022
    assert all(row["v1_111_band"] == "Low Stability" for row in year_2022)
    september = _by_date(rows)["2011-09-01"]
    assert september["b_index"] == 47.84
    assert september["rent_burden_30"] == 53.4
    assert september["housing_delinquency"] == 10.5


def test_current_reading_is_the_1_1_1_restatement():
    current = current_reading()
    scored = current["scored"]
    assert current["publication_date"] == "2026-10-09"
    assert current["published_methodology"] == "1.1.0"
    assert current["published_file_index"] == 57.66
    assert current["published_index"] == 57.66
    assert scored["v1"]["index"] == 57.50
    assert scored["v1"]["band"] == "Moderate Stability"
    assert current["values"]["homelessness_rate"] == 0.22
    assert current["values"]["trust_in_government"] == 39
    for name in BASKET_ADDONS:
        basket = scored["baskets"][name]
        assert basket["band"] == "Moderate Stability"
        assert basket["index"] > scored["v1"]["index"]


def test_october_2025_gap_is_not_filled_in():
    october = _by_date(build_v2_rows())["2025-10-01"]
    assert october["inflation_rate"] is None
    assert october["food_cpi_yoy"] is None
    assert october["prime_age_epop"] is None
    assert october["unemployment_rate"] is None
    assert october["a_index"] == october["v1_111_index"]
    assert october["v1_partial_index"] == 38.72
    assert october["v1_partial_band"] == "Critical Instability"
    assert october["b_band"] == "Moderate Stability"
    assert october["c_band"] == "Moderate Stability"


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


def test_debt_and_credit_fixtures_cover_the_stress_windows():
    locked = load_fixtures().debt_to_gdp
    full = parse_series_csv(
        (PACKAGE_DIR / "fixtures" / "v2" / "GFDEGDQ188S_full.csv").read_text(encoding="utf-8")
    )
    extra = parse_series_csv(
        (PACKAGE_DIR / "fixtures" / "v2" / "GFDEGDQ188S_published_extra.csv").read_text(
            encoding="utf-8"
        )
    )
    overlap = set(locked) & set(full)
    assert overlap
    assert all(abs(locked[day] - full[day]) < 1e-9 for day in overlap)
    assert extra["2025-10-01"] == 122.56815
    assert full["2025-10-01"] == 122.56815
    credit = {}
    with (PACKAGE_DIR / "fixtures" / "v2" / "NFCICREDIT_weekly.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            credit[row["friday"]] = float(row["credit"])
    assert credit["1973-03-16"] == -3.159
    assert credit["2008-12-05"] == 2.808


def test_within_month_v1_is_flat():
    weekly = weekly_volatility()
    by_key = {(row["basket"], row["sample"]): row for row in weekly}
    for basket in ("v1_111", "a_labor_food", "b_cost_of_living"):
        row = by_key[(basket, "within_month")]
        assert row["share_flat"] == 1.0
        assert row["mean_abs_change"] == 0.0
    credit = by_key[("c_financial", "within_month")]
    assert credit["share_flat"] < 0.05
    assert credit["mean_abs_change"] > 0


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
    assert "2026-10-09 57.50 Moderate Stability methodology 1.1.1 restatement" in printed
    monthly = list(csv.DictReader((tmp_path / MONTHLY_NAME).open(encoding="utf-8")))
    assert monthly[0]["candidate_label"] == CANDIDATE_LABEL
    assert monthly[0]["methodology_reference"] == "1.1.1"
    note_text = note.read_text(encoding="utf-8")
    assert "Stay on methodology 1.1.1." in note_text
    assert "not a methodology version" in note_text
    assert "77.28" in note_text
    assert "57.66" in note_text
    v1_dir = tmp_path / "v1"
    assert v1_main(["--output", str(v1_dir), "--windows", "2020"]) == 0
    assert (v1_dir / "replay_partial.csv").exists()
    assert not (v1_dir / MONTHLY_NAME).exists()


def test_committed_v2_tables_match_the_harness(tmp_path):
    rows = build_v2_rows()
    fresh = [csv_fields(row) for row in rows]
    with (V2_OUTPUT_DIR / MONTHLY_NAME).open(newline="", encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert list(committed[0]) == list(COLUMNS)
    assert committed == fresh
    note = tmp_path / "note.md"
    write_outputs(tmp_path, note)
    for name in (MONTHLY_NAME, SUMMARY_NAME, WEEKLY_NAME, CHART_NAME):
        assert (tmp_path / name).read_bytes() == (V2_OUTPUT_DIR / name).read_bytes()
    committed_note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note.read_text(encoding="utf-8") == committed_note
    assert "Stay on methodology 1.1.1." in committed_note
    assert "57.50" in committed_note
    assert "57.11" in committed_note
    assert "57.66" in committed_note
    assert "77.28" in committed_note
    assert "NFCICREDIT" in committed_note
    assert "B25070" in committed_note
    assert "38.72" in committed_note
    assert "2011-09-01" in committed_note
    assert "2008-10-01" in committed_note
    assert "2020-04-01" in committed_note
    assert "2022-06-01" in committed_note
    assert "so it pulls the basket up, so" not in committed_note
    assert "so it pulls the basket down, so" not in committed_note
    partial = (OUTPUT_DIR / "replay_partial.csv").read_text(encoding="utf-8")
    assert "2022-06-01" not in partial
    assert "v2_candidate" not in partial
