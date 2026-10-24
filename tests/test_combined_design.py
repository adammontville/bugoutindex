# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""The combined 2.0 research replay stays off the live score and matches its note."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.backtest.combined_design import (
    CALIBRATION_DIR,
    CHART_NAME,
    COLUMNS,
    DEBT_REFERENCE_END,
    MONTHLY_NAME,
    NOTE_NAME,
    OUTPUT_DIR,
    PACKAGE_DIR,
    REFERENCE_END,
    SUMMARY_NAME,
    VIX_REFERENCE_END,
    VIX_REFERENCE_START,
    WEEKLY_NAME,
    W1,
    W2,
    assemble,
    csv_fields,
    current_reading,
    fit_endpoints,
    load_bundle,
    main,
    percentile,
    render_markdown,
    render_svg,
)
from runtime.backtest.harness import load_fixtures, load_published_raws, score_published_inputs
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
        assert "combined_design" not in text
        assert "NFCICREDIT" not in text
    assert sum(WEIGHTS.values()) == 0.72
    assert METRIC_RANGES["inflation_rate"] == (-10, 15)
    assert METRIC_RANGES["incident_rate"] == (500, 8000)
    assert METRIC_RANGES["debt_to_gdp_ratio"] == (0, 200)
    assert round(sum(W1.values()), 10) == 0.72
    assert round(sum(W2.values()), 10) == 0.72


def test_reference_files_stop_before_the_replay_and_match_on_overlap():
    assert max(_dates(CALIBRATION_DIR / "CPIAUCSL.csv")) == REFERENCE_END
    assert max(_dates(CALIBRATION_DIR / "UNRATE.csv")) == REFERENCE_END
    assert max(_dates(CALIBRATION_DIR / "GFDEGDQ188S.csv")) == DEBT_REFERENCE_END
    assert min(_dates(CALIBRATION_DIR / "VIXCLS_monthly.csv")) == VIX_REFERENCE_START
    assert max(_dates(CALIBRATION_DIR / "VIXCLS_monthly.csv")) == VIX_REFERENCE_END
    bundle = load_bundle()
    overlap = set(bundle["vix_reference"]) & set(bundle["vix_replay"])
    assert overlap == {day for day in bundle["vix_reference"] if day.startswith("2006")}
    assert all(abs(bundle["vix_reference"][day] - bundle["vix_replay"][day]) < 1e-6 for day in overlap)
    locked = load_fixtures().debt_to_gdp
    replay_debt = {}
    with (CALIBRATION_DIR / "GFDEGDQ188S_replay.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            replay_debt[row["observation_date"]] = float(row["GFDEGDQ188S"])
    debt_overlap = set(locked) & set(replay_debt)
    assert debt_overlap
    assert all(abs(locked[day] - replay_debt[day]) < 1e-9 for day in debt_overlap)


def test_percentile_and_frozen_endpoints():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    ends = fit_endpoints(load_bundle())
    assert round(ends["inflation"]["lo"], 5) == 1.40218
    assert round(ends["unemployment"]["lo"], 1) == 4.0
    assert round(ends["unemployment"]["hi"], 1) == 10.1
    assert ends["vix"]["n"] == 204
    assert ends["debt_yoy"]["lo"] < 0 < ends["debt_yoy"]["hi"]
    ranges = METRIC_RANGES["incident_rate"]
    assert ranges == (500, 8000)


def test_key_readings_and_the_recommendation():
    report = assemble()
    rows = _by_date(report["rows"])
    today = report["today"]
    assert rows["2008-10-01"]["v1_index"] == 56.89
    assert rows["2020-04-01"]["v1_index"] == 50.98
    assert today["v1_index"] == 57.50
    assert today["published_file_index"] == 57.66
    assert today["published_methodology"] == "1.1.0"
    assert rows["2008-10-01"]["w2_index"] == 44.60
    assert rows["2009-10-01"]["w2_index"] == 42.77
    assert rows["2020-03-01"]["w2_index"] == 63.22
    assert rows["2020-04-01"]["w2_index"] == 42.80
    assert rows["2022-06-01"]["w2_index"] == 64.49
    assert rows["2026-08-01"]["w2_index"] == 69.64
    assert today["w2_index"] == 69.39
    assert today["w2_band"] == "Moderate Stability"
    assert today["w1_band"] == "High Stability"
    assert rows["2020-04-01"]["w1_band"] == "Critical Instability"
    assert rows["2020-04-01"]["w2_band"] == "Low Stability"
    assert rows["2025-10-01"]["inflation_rate"] is None
    assert rows["2025-10-01"]["unemployment_rate"] is None
    critical = [
        row["date"]
        for row in report["rows"]
        if row["sample"] == "out_of_sample" and row["w2_band"] == "Critical Instability"
    ]
    assert critical == ["2010-05-01", "2011-08-01", "2011-09-01", "2011-10-01"]
    calm = [
        row
        for row in report["rows"]
        if "2015-01-01" <= row["date"] <= "2019-12-01"
    ]
    assert all(row["w2_band"] in ("High Stability", "Moderate Stability") for row in calm)
    assert min(row["w2_index"] for row in calm) > max(
        rows[day]["w2_index"] for day in ("2008-10-01", "2009-10-01", "2020-04-01")
    )
    assert report["recommend"] is True
    assert report["ceiling"] == 69.29
    assert current_reading()["w2_index"] == 69.39


def test_backtest_workflow_does_not_publish():
    text = (ROOT / ".github" / "workflows" / "backtest.yml").read_text(encoding="utf-8")
    assert "weekly_run" not in text
    assert "contents: read" in text
    assert "schedule:" not in text
    assert "test_combined_design.py" in text
    assert "test_v2_candidate.py" in text


def test_cli_prints_the_lock_and_writes_a_labeled_note(tmp_path, capsys):
    note = tmp_path / "note.md"
    code = main(["--check-locked", "--output", str(tmp_path), "--note", str(note)])
    assert code == 0
    printed = capsys.readouterr().out
    assert "2026-09-19 57.11 Moderate Stability methodology 1.0.0" in printed
    note_text = note.read_text(encoding="utf-8")
    assert "Recommendation: adopt W2" in note_text
    assert "69.39" in note_text
    assert "2.0.0" in note_text
    assert "does not change `compute_index`" in note_text
    assert (tmp_path / MONTHLY_NAME).exists()
    assert (tmp_path / SUMMARY_NAME).exists()
    assert (tmp_path / WEEKLY_NAME).exists()
    assert (tmp_path / CHART_NAME).exists()


def test_committed_tables_match_the_harness():
    report = assemble()
    fresh = [csv_fields(row) for row in report["rows"]]
    with (OUTPUT_DIR / MONTHLY_NAME).open(newline="", encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert list(committed[0]) == list(COLUMNS)
    assert committed == fresh
    note = (PACKAGE_DIR / NOTE_NAME).read_text(encoding="utf-8")
    assert note == render_markdown(report)
    assert (OUTPUT_DIR / CHART_NAME).read_text(encoding="utf-8") == render_svg(report["rows"])
    assert "October 2025" in note
    assert "57.50" in note
    assert "57.66" in note
    assert "methodology 1.1.0" in note
