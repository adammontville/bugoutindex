# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Locks the v1.0.0 formula: one module, published inputs, inversion, and clamp."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.processing import normalize_metric
from runtime.processing.formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    calculate_category_score,
    compute_index,
    interpret,
    normalize,
    score_metric,
    stability_css_class,
)
from runtime.processing.normalize import normalize_metric as normalize_metric_wrapper
from runtime.processing.scoring_v1 import calculate_category_score as scoring_v1_score
from runtime.publish.weekly_run import (
    CORE_METRICS as WEEKLY_CORE_METRICS,
    METRIC_RANGES as WEEKLY_RANGES,
    WEIGHTS as WEEKLY_WEIGHTS,
    compute_index as weekly_compute_index,
    interpret as weekly_interpret,
    normalize as weekly_normalize,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DATE = "2026-09-19"
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"
LATEST_JSON = ROOT / "docs" / "data" / "latest.json"


def _published_row() -> dict:
    with WEEKLY_CSV.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == PUBLISHED_DATE]
    assert len(rows) == 1, f"expected one {PUBLISHED_DATE} history row"
    return rows[0]


def _published_raws() -> dict:
    """19 September 2026 raw inputs from the weekly CSV and latest.json."""
    row = _published_row()
    raws = {metric: float(row[metric]) for metric in CORE_METRICS}

    latest = json.loads(LATEST_JSON.read_text())
    history = [
        item for item in latest["history"]["bugout_index"] if item["date"] == PUBLISHED_DATE
    ]
    assert history, "19 September 2026 row missing from docs/data/latest.json history"
    for metric in CORE_METRICS:
        assert float(history[-1][metric]) == raws[metric]

    if latest.get("publication_date") == PUBLISHED_DATE:
        assert latest["bugout_index"] == 57.11
        assert latest["interpretation"]["band"] == "Moderate Stability"
        for metric in CORE_METRICS:
            assert float(latest["metrics"][metric]["raw"]) == raws[metric]
    return raws


def _fetcher_payload(raws: dict) -> dict:
    return {metric: {"data": {metric: value}} for metric, value in raws.items()}


def test_processing_package_exports_normalize_metric():
    """The old collection failure was an empty processing package."""
    assert normalize_metric(5, 0, 20) == 75.0
    assert normalize_metric is normalize


def test_generic_linear_map():
    assert normalize_metric(5, 0, 20) == 75.0  # higher raw → less stable
    assert normalize_metric(150, 50, 150) == 0.0
    assert normalize_metric(50, 0, 100) == 50.0


def test_trust_41_normalizes_to_51_25():
    scored = score_metric("trust_in_government", 41)
    without_inversion = normalize(41, 0, 80, inverse=False)
    assert round(scored, 2) == 51.25
    assert round(without_inversion, 2) == 48.75
    assert round(scored, 2) != round(without_inversion, 2)
    assert METRIC_RANGES["trust_in_government"] == (0, 80)


def test_inflation_4_percent_normalizes_to_44_on_published_endpoints():
    assert METRIC_RANGES["inflation_rate"] == (-10, 15)
    assert round(score_metric("inflation_rate", 4), 2) == 44.0
    assert round(normalize(4, -10, 15), 2) == 44.0


def test_september_19_2026_scores_57_11_moderate_stability():
    raws = _published_raws()
    scored = compute_index(_fetcher_payload(raws))
    row = _published_row()

    assert scored["index"] == 57.11
    assert float(row["bugout_index"]) == 57.11
    assert interpret(scored["index"]) == {
        "band": "Moderate Stability",
        "risk": "Warning Signs",
        "band_key": "moderate",
    }
    for metric in CORE_METRICS:
        assert scored["metrics"][metric]["normalized"] == float(row[f"{metric}_normalized"])
        assert scored["metrics"][metric]["normalized"] == round(score_metric(metric, raws[metric]), 2)


def test_index_divides_by_total_weight():
    """A plain sum of weighted scores is about 41.12 (Low Stability), not 57.11."""
    raws = _published_raws()
    weighted_sum = sum(score_metric(metric, raws[metric]) * WEIGHTS[metric] for metric in CORE_METRICS)
    assert sum(WEIGHTS.values()) == 0.72
    assert round(weighted_sum, 2) == 41.12
    assert interpret(round(weighted_sum, 2))["band"] == "Low Stability"

    scored = compute_index(_fetcher_payload(raws))
    assert scored["index"] == round(weighted_sum / sum(WEIGHTS.values()), 2) == 57.11
    assert scored["index"] != round(weighted_sum, 2)


def test_missing_metric_shrinks_the_denominator():
    scored = compute_index({"inflation_rate": {"data": {"inflation_rate": -10}}})
    assert scored["index"] == 100.0
    assert scored["index"] != round(100 * WEIGHTS["inflation_rate"] / sum(WEIGHTS.values()), 2)


def test_normalize_clamps_to_0_100_after_inversion():
    assert normalize(100, -10, 15) == 0.0
    assert normalize(-100, -10, 15) == 100.0
    assert (1 - ((100 - (-10)) / (15 - (-10)))) * 100 < 0
    assert normalize(1000, 0, 80, inverse=True) == 100.0
    assert normalize(-100, 0, 80, inverse=True) == 0.0
    assert 100 - (1 - ((1000 - 0) / (80 - 0))) * 100 > 100
    assert normalize(3, 3, 3) == 0.0


def test_simulator_path_matches_weekly_path_in_range_and_when_clamped():
    raws = _published_raws()
    weekly = compute_index(_fetcher_payload(raws))["index"]
    simulated = round(calculate_category_score(raws), 2)
    assert simulated == weekly == 57.11

    legacy_dicts = {metric: {metric: value} for metric, value in raws.items()}
    assert round(calculate_category_score(legacy_dicts), 2) == 57.11

    clamped = {metric: METRIC_RANGES[metric][0] for metric in CORE_METRICS}
    clamped["inflation_rate"] = 100  # above the 15 endpoint
    weekly_clamped = compute_index(_fetcher_payload(clamped))["index"]
    assert score_metric("inflation_rate", 100) == 0.0
    assert round(calculate_category_score(clamped), 2) == weekly_clamped


def test_publishers_share_the_formula_module():
    assert weekly_compute_index is compute_index
    assert weekly_normalize is normalize is normalize_metric_wrapper
    assert weekly_interpret is interpret
    assert WEEKLY_CORE_METRICS is CORE_METRICS
    assert WEEKLY_RANGES is METRIC_RANGES
    assert WEEKLY_WEIGHTS is WEIGHTS
    assert scoring_v1_score is calculate_category_score


def test_other_publishers_do_not_keep_a_second_copy():
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text()
    simulator = (ROOT / "runtime" / "pages" / "boi_simulator.py").read_text()
    calculate_index = (ROOT / "runtime" / "processing" / "calculate_index.py").read_text()
    normalize_py = (ROOT / "runtime" / "processing" / "normalize.py").read_text()
    scoring = (ROOT / "runtime" / "processing" / "scoring_v1.py").read_text()

    assert "import runtime.processing.formula as _formula" in weekly
    assert "def normalize(" not in weekly
    assert "def compute_index(" not in weekly
    assert "def interpret(" not in weekly

    assert "from processing.formula import" in simulator
    assert "(-10, 15)" not in simulator
    assert "0.15" not in simulator

    assert "from runtime.processing.formula import" in calculate_index
    assert "def normalize_metric(" not in calculate_index
    assert "def calculate_category_score(" not in calculate_index
    assert "(-10, 15)" not in calculate_index

    assert "def normalize_metric(" not in normalize_py
    assert "from .formula import normalize as normalize_metric" in normalize_py
    assert "def calculate_category_score(" not in scoring
    assert "from .formula import calculate_category_score, normalize_metric" in scoring


def test_four_bands_and_streamlit_classes():
    assert interpret(70)["band"] == "High Stability"
    assert interpret(69.99)["band"] == "Moderate Stability"
    assert interpret(55)["band"] == "Moderate Stability"
    assert interpret(54.99)["band"] == "Low Stability"
    assert interpret(40)["band"] == "Low Stability"
    assert interpret(39.99)["band"] == "Critical Instability"
    assert stability_css_class(70) == "stable"
    assert stability_css_class(57.11) == "moderate"
    assert stability_css_class(40) == "severe"
    assert stability_css_class(39.99) == "critical"
