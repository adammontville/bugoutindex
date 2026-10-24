# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Endpoint and band research stays off the live score and matches its note."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.backtest.endpoint_calibration import (
    CALIBRATION_DIR,
    CHART_NAME,
    COLUMNS,
    DEBT_REFERENCE_END,
    MONTHLY_NAME,
    NOTE_NAME,
    OUTPUT_DIR,
    PACKAGE_DIR,
    REFERENCE_END,
    STRESS_MONTH,
    SUMMARY_NAME,
    WEEKLY_NAME,
    build_rows,
    csv_fields,
    current_reading,
    inflation_sample,
    load_bundle,
    main,
    percentile,
    research_ranges,
    weekly_volatility,
    write_outputs,
)
from runtime.backtest.harness import (
    OUTPUT_DIR as V1_OUTPUT_DIR,
    load_fixtures,
    load_published_raws,
    score_published_inputs,
)
from runtime.processing.formula import CORE_METRICS, METRIC_RANGES, WEIGHTS
from runtime.processing.formula import compute_index as formula_compute_index

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


def _by_date(rows):
    return {row["date"]: row for row in rows}


def _payload(raws):
    return {metric: {"data": {metric: value}} for metric, value in raws.items()}


def _dates(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        return [row["observation_date"] for row in csv.DictReader(handle)]


def test_locked_score_and_live_path_are_untouched():
    raws = load_published_raws()
    assert score_published_inputs(raws)["index"] == 57.11
    assert formula_compute_index(_payload(raws))["index"] == 57.11
    latest = json.loads((ROOT / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["methodology_version"] == "1.1.0"
    assert latest["bugout_index"] == 57.66
    published = {metric: float(latest["metrics"][metric]["raw"]) for metric in CORE_METRICS}
    assert formula_compute_index(_payload(published))["index"] == 57.66
    schema = (ROOT / "runtime" / "publish" / "snapshot_schema.py").read_text(encoding="utf-8")
    assert 'METHODOLOGY_VERSION = "1.1.1"' in schema
    for path in LIVE_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "endpoint_calibration" not in text
        assert "NFCICREDIT" not in text
    assert sum(WEIGHTS.values()) == 0.72
    assert METRIC_RANGES["inflation_rate"] == (-10, 15)
    assert METRIC_RANGES["incident_rate"] == (500, 8000)
    assert METRIC_RANGES["debt_to_gdp_ratio"] == (0, 200)


def test_reference_files_stop_before_the_replay():
    assert max(_dates(CALIBRATION_DIR / "CPIAUCSL.csv")) == REFERENCE_END
    assert max(_dates(CALIBRATION_DIR / "UNRATE.csv")) == REFERENCE_END
    assert max(_dates(CALIBRATION_DIR / "GFDEGDQ188S.csv")) == DEBT_REFERENCE_END
    assert min(_dates(CALIBRATION_DIR / "GFDEGDQ188S_replay.csv")) == "2006-10-01"
    replay_cpi = {}
    with (PACKAGE_DIR / "fixtures" / "v2" / "CPIAUCSL.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            replay_cpi[row["observation_date"]] = float(row["CPIAUCSL"])
    reference_cpi = {}
    with (CALIBRATION_DIR / "CPIAUCSL.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            reference_cpi[row["observation_date"]] = float(row["CPIAUCSL"])
    overlap = set(replay_cpi) & set(reference_cpi)
    assert overlap
    assert all(abs(replay_cpi[day] - reference_cpi[day]) < 1e-9 for day in overlap)
    locked = load_fixtures().debt_to_gdp
    replay_debt = {}
    with (CALIBRATION_DIR / "GFDEGDQ188S_replay.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            replay_debt[row["observation_date"]] = float(row["GFDEGDQ188S"])
    debt_overlap = set(locked) & set(replay_debt)
    assert debt_overlap
    assert all(abs(locked[day] - replay_debt[day]) < 1e-9 for day in debt_overlap)


def test_percentile_is_type_7_and_the_stress_month_is_the_inflation_peak():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    bundle = load_bundle()
    sample = inflation_sample(bundle, "1970-01-01", REFERENCE_END)
    peak = max(sample, key=lambda item: item[1])
    assert peak[0] == STRESS_MONTH
    ranges = research_ranges(bundle)
    assert ranges["inflation_rate"][0] < ranges["inflation_rate"][1]
    assert ranges["unemployment_rate"] == (4.0, 10.1) or (
        abs(ranges["unemployment_rate"][0] - 4.0) < 1e-9
        and abs(ranges["unemployment_rate"][1] - 10.1) < 1e-9
    )
    assert ranges["debt_to_gdp_ratio"][1] < 66
    assert ranges["incident_rate"] == METRIC_RANGES["incident_rate"]
    assert ranges["homelessness_rate"] == METRIC_RANGES["homelessness_rate"]
    assert ranges["trust_in_government"] == METRIC_RANGES["trust_in_government"]


def test_replay_separates_only_when_the_endpoints_move():
    rows, context = build_rows()
    by_date = _by_date(rows)
    october = by_date["2008-10-01"]
    april = by_date["2020-04-01"]
    june = by_date["2022-06-01"]
    assert october["v1_index"] == 56.89
    assert october["v1_band"] == "Moderate Stability"
    assert april["v1_index"] == 50.98
    assert april["v1_band"] == "Low Stability"
    assert june["v1_band"] == "Low Stability"
    assert all(row["v1_band"] != "High Stability" for row in rows)
    assert all(row["v1_band"] != "Critical Instability" for row in rows)
    assert all(row["a_band"] != "High Stability" for row in rows)
    assert all(row["a_band"] != "Critical Instability" for row in rows)
    current = current_reading(context=context)
    assert current["v1_index"] == 57.50
    assert current["v1_band"] == "Moderate Stability"
    assert current["published_index"] == 57.66
    assert current["v1_band"] == october["v1_band"]
    assert current["b_band"] == october["b_band"]
    assert current["a_index"] > october["a_index"]
    assert current["a_band"] != october["a_band"]
    assert october["a_band"] == "Low Stability"
    assert current["a_band"] == "Moderate Stability"
    assert october["c_band"] == "Critical Instability"
    assert current["c_band"] == "High Stability"
    assert context["ranges"]["debt_to_gdp_ratio"][1] < october["debt_to_gdp_ratio"]
    year_2022 = [row for row in rows if row["window"] == "2022"]
    assert all(row["v1_band"] == "Low Stability" for row in year_2022)
    calm = [row for row in rows if row["window"] == "2015_2019"]
    assert all(row["a_band"] == "Moderate Stability" for row in calm)
    weekly = weekly_volatility(rows)
    within = next(row for row in weekly if row["series"] == "v1" and row["sample"] == "within_month")
    assert within["share_flat"] == 1.0
    assert within["mean_abs_change"] == 0.0


def test_backtest_workflow_does_not_publish():
    text = (ROOT / ".github" / "workflows" / "backtest.yml").read_text(encoding="utf-8")
    assert "weekly_run" not in text
    assert "contents: read" in text
    assert "schedule:" not in text
    assert "test_endpoint_calibration.py" in text


def test_cli_prints_the_lock(tmp_path, capsys):
    note = tmp_path / "note.md"
    code = main(["--check-locked", "--output", str(tmp_path), "--note", str(note)])
    assert code == 0
    printed = capsys.readouterr().out
    assert "2026-09-19 57.11 Moderate Stability methodology 1.0.0" in printed
    assert "2026-10-09 57.50 Moderate Stability methodology 1.1.1 restatement" in printed
    note_text = note.read_text(encoding="utf-8")
    assert "Stay on methodology 1.1.1." in note_text
    assert "methodology 2.0.0" in note_text
    assert "not a methodology version" in note_text


def test_committed_tables_match_the_harness(tmp_path):
    rows, _context = build_rows()
    fresh = [csv_fields(row) for row in rows]
    with (OUTPUT_DIR / MONTHLY_NAME).open(newline="", encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert list(committed[0]) == list(COLUMNS)
    assert committed == fresh
    note = tmp_path / "note.md"
    write_outputs(tmp_path, note)
    for name in (MONTHLY_NAME, SUMMARY_NAME, WEEKLY_NAME, CHART_NAME):
        assert (tmp_path / name).read_bytes() == (OUTPUT_DIR / name).read_bytes()
    committed_note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note.read_text(encoding="utf-8") == committed_note
    assert "69.29" in committed_note
    assert "2008-10-01" in committed_note
    assert "2020-04-01" in committed_note
    assert "2022-06-01" in committed_note
    assert "64.67" in committed_note
    partial = (V1_OUTPUT_DIR / "replay_partial.csv").read_text(encoding="utf-8")
    assert "endpoint_calibration" not in partial
