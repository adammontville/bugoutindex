# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Parked and not-yet-sourced stubs must not report fictional success."""
from __future__ import annotations

import importlib
from pathlib import Path

from runtime.data.fetch.not_wired import NotWiredError
from runtime.data.fetch_data import FETCH_INTERVALS
from runtime.processing.formula import CORE_METRICS, WEIGHTS

ROOT = Path(__file__).resolve().parents[1]
WEEKLY = ROOT / "runtime" / "publish" / "weekly_run.py"

# Modules that used to return status success plus a hardcoded sample.
UNWIRED = (
    "runtime.data.fetch.fetch_air_quality_index",
    "runtime.data.fetch.fetch_healthcare_capacity",
    "runtime.data.fetch.fetch_natural_disaster_frequency",
    "runtime.data.fetch.fetch_grid_outages",
    "runtime.data.fetch.fetch_food_price_index",
)

# Legacy cache script keys. These must not be scheduled while the stubs refuse.
UNSCHEDULED = (
    "air_quality_index",
    "healthcare_capacity",
    "natural_disaster_frequency",
    "grid_outages",
    "food_price_index",
)


def test_unwired_fetchers_raise_and_do_not_return_success():
    for module_name in UNWIRED:
        module = importlib.import_module(module_name)
        try:
            result = module.fetch()
        except NotWiredError as exc:
            message = str(exc)
            assert "NOT_WIRED" in message
            assert "success" not in message.lower()
            continue
        raise AssertionError(f"{module_name}.fetch() returned {result!r} instead of raising NotWiredError")


def test_legacy_cache_does_not_schedule_unwired_metrics():
    for metric in UNSCHEDULED:
        assert metric not in FETCH_INTERVALS


def test_weekly_publisher_does_not_name_unwired_fetchers():
    text = WEEKLY.read_text()
    for module_name in UNWIRED:
        stub = module_name.rsplit(".", 1)[-1]
        assert stub not in text
    assert list(CORE_METRICS) == [
        "inflation_rate",
        "incident_rate",
        "unemployment_rate",
        "debt_to_gdp_ratio",
        "homelessness_rate",
        "trust_in_government",
    ]
    assert set(WEIGHTS) == set(CORE_METRICS)
    assert abs(sum(WEIGHTS.values()) - 0.72) < 1e-9
