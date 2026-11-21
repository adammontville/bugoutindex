# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""FRED '.' and empty observations are skipped, not parsed as numbers."""
from __future__ import annotations

import json
from pathlib import Path

from runtime.data.fetch.fetch_debt_to_gdp_ratio import fetch as fetch_debt
from runtime.data.fetch.fetch_inflation_rate import (
    fetch as fetch_inflation,
    inflation_rate_from_levels,
    select_inflation,
)
from runtime.data.fetch.fetch_markets import _fetch_dxy_from_fred
from runtime.data.fetch.fetch_pulse import fetch as fetch_pulse
from runtime.data.fetch.fetch_unemployment_rate import fetch as fetch_unemployment
from runtime.data.fetch.fred_observations import (
    CPI_OBSERVATION_LIMIT,
    is_missing_fred_value,
    parse_numeric_observations,
)
from runtime.processing.formula import METRIC_RANGES, WEIGHTS, compute_index

ROOT = Path(__file__).resolve().parents[1]
CPI_FIXTURE = ROOT / "tests" / "fixtures" / "cpiaucsl_observations_2026-11-21.json"

# Levels that make the three gap cases obvious. 12 months apart, not neighbors.
SEP_2026 = 330.0
SEP_2025 = 300.0
AUG_2026 = 320.0
AUG_2025 = 290.0


def _response(observations):
    class Response:
        def json(self):
            return {"observations": observations}

    return Response()


def test_missing_marker_is_dot_or_empty_and_zero_is_kept():
    assert is_missing_fred_value(".")
    assert is_missing_fred_value("")
    assert is_missing_fred_value("  ")
    assert is_missing_fred_value(None)
    assert is_missing_fred_value(0) is False
    assert is_missing_fred_value("0") is False
    points = parse_numeric_observations([
        {"date": "2026-10-01", "value": "."},
        {"date": "2026-09-01", "value": ""},
        {"date": "2026-08-01", "value": " 4.2 "},
    ])
    assert points == [{"date": "2026-08-01", "value": 4.2}]


def test_inflation_skips_dot_at_the_latest_observation():
    chosen = select_inflation([
        {"date": "2026-10-01", "value": "."},
        {"date": "2026-09-01", "value": str(SEP_2026)},
        {"date": "2026-08-01", "value": str(AUG_2026)},
        {"date": "2025-09-01", "value": str(SEP_2025)},
        {"date": "2025-08-01", "value": str(AUG_2025)},
    ])
    assert chosen["observation_date"] == "2026-09-01"
    assert chosen["comparison_date"] == "2025-09-01"
    assert chosen["inflation_rate"] == inflation_rate_from_levels(SEP_2026, SEP_2025)
    assert chosen["inflation_rate"] == ((SEP_2026 - SEP_2025) / SEP_2025) * 100


def test_inflation_ignores_dot_in_the_middle_of_the_series():
    chosen = select_inflation([
        {"date": "2026-09-01", "value": str(SEP_2026)},
        {"date": "2026-07-01", "value": "."},
        {"date": "2026-08-01", "value": str(AUG_2026)},
        {"date": "2025-09-01", "value": str(SEP_2025)},
        {"date": "2025-08-01", "value": str(AUG_2025)},
        {"date": "2025-07-01", "value": "280"},
    ])
    assert chosen["observation_date"] == "2026-09-01"
    assert chosen["comparison_date"] == "2025-09-01"
    assert chosen["inflation_rate"] == inflation_rate_from_levels(SEP_2026, SEP_2025)
    assert "2026-07-01" not in {
        chosen["observation_date"],
        chosen["comparison_date"],
    }


def test_inflation_steps_back_when_the_year_ago_month_is_dot():
    # October 2026 has a real index. October 2025 is missing. Do not
    # average neighbors and do not borrow November or August as October's
    # comparison month. Step back to September, where both prints exist.
    chosen = select_inflation([
        {"date": "2026-10-01", "value": "337.476"},
        {"date": "2026-09-01", "value": "336.298"},
        {"date": "2026-08-01", "value": "334.131"},
        {"date": "2025-11-01", "value": "325.063"},
        {"date": "2025-10-01", "value": "."},
        {"date": "2025-09-01", "value": "324.245"},
        {"date": "2025-08-01", "value": "323.291"},
    ])
    assert chosen["observation_date"] == "2026-09-01"
    assert chosen["comparison_date"] == "2025-09-01"
    assert chosen["current_cpi"] == 336.298
    assert chosen["previous_cpi"] == 324.245
    assert chosen["inflation_rate"] == inflation_rate_from_levels(336.298, 324.245)
    assert chosen["inflation_rate"] != inflation_rate_from_levels(337.476, 325.063)
    assert chosen["inflation_rate"] != inflation_rate_from_levels(337.476, 324.245)


def test_inflation_empty_comparison_month_steps_back_and_a_gap_is_not_invented():
    chosen = select_inflation([
        {"date": "2026-10-01", "value": "110"},
        {"date": "2026-09-01", "value": "108"},
        {"date": "2025-10-01", "value": ""},
        {"date": "2025-09-01", "value": "100"},
    ])
    assert chosen["observation_date"] == "2026-09-01"
    assert chosen["inflation_rate"] == inflation_rate_from_levels(108, 100)
    assert select_inflation([
        {"date": "2026-10-01", "value": "110"},
        {"date": "2026-09-01", "value": "."},
        {"date": "2025-10-01", "value": "."},
        {"date": "2025-09-01", "value": ""},
    ]) is None


def test_recorded_cpiaucsl_fixture_uses_september_2026(monkeypatch):
    fixture = json.loads(CPI_FIXTURE.read_text(encoding="utf-8"))
    observations = fixture["observations"]
    missing = [row["date"] for row in observations if row["value"] == "."]
    assert missing == ["2025-10-01"]
    assert observations[-1] == {"date": "2026-10-01", "value": "337.476"}

    chosen = select_inflation(observations)
    assert chosen["observation_date"] == "2026-09-01"
    assert chosen["comparison_date"] == "2025-09-01"
    assert chosen["inflation_rate"] == ((336.298 - 324.245) / 324.245) * 100

    seen = {}

    def fake_get(_url, params=None, **_kwargs):
        seen.update(params)
        return _response(observations)

    monkeypatch.setattr(
        "runtime.data.fetch.fetch_inflation_rate.get_with_retry", fake_get
    )
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_inflation_rate.get_secret", lambda _key: "test-key"
    )
    result = fetch_inflation()
    assert result["status"] == "success"
    assert result["observation_date"] == "2026-09-01"
    assert result["fetched_at"] == "2026-09-01"
    assert result["data"]["inflation_rate"] == chosen["inflation_rate"]
    assert seen["series_id"] == "CPIAUCSL"
    assert seen["limit"] == CPI_OBSERVATION_LIMIT
    assert seen["limit"] > 1


def test_inflation_fetch_does_not_invent_a_rate_when_no_pair_exists(monkeypatch):
    def fake_get(_url, params=None, **_kwargs):
        return _response([
            {"date": "2026-10-01", "value": "."},
            {"date": "2026-09-01", "value": ""},
        ])

    monkeypatch.setattr(
        "runtime.data.fetch.fetch_inflation_rate.get_with_retry", fake_get
    )
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_inflation_rate.get_secret", lambda _key: "test-key"
    )
    result = fetch_inflation()
    assert result["status"] == "error"
    assert "data" not in result
    assert "inflation_rate" not in json.dumps(result)


def test_unemployment_and_debt_skip_dot_and_empty_at_the_latest_row(monkeypatch):
    def fake_get(_url, params=None, **_kwargs):
        assert params["limit"] > 1
        latest = "2026-10-01" if params["series_id"] == "UNRATE" else "2026-04-01"
        previous = "2026-09-01" if params["series_id"] == "UNRATE" else "2026-01-01"
        value = "4.2" if params["series_id"] == "UNRATE" else "121.5"
        return _response([
            {"date": latest, "value": "."},
            {"date": previous, "value": ""},
            {"date": "2025-10-01", "value": value},
        ])

    monkeypatch.setattr(
        "runtime.data.fetch.fetch_unemployment_rate.get_with_retry", fake_get
    )
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_unemployment_rate.get_secret", lambda _key: "test-key"
    )
    unemployment = fetch_unemployment()
    assert unemployment["status"] == "success"
    assert unemployment["observation_date"] == "2025-10-01"
    assert unemployment["data"]["unemployment_rate"] == 4.2

    monkeypatch.setattr(
        "runtime.data.fetch.fetch_debt_to_gdp_ratio.get_with_retry", fake_get
    )
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_debt_to_gdp_ratio.get_secret", lambda _key: "test-key"
    )
    debt = fetch_debt()
    assert debt["status"] == "success"
    assert debt["observation_date"] == "2025-10-01"
    assert debt["data"]["debt_to_gdp_ratio"] == 121.5


def test_pulse_and_dollar_index_skip_dot(monkeypatch):
    def fake_get(_url, params=None, **_kwargs):
        assert params["limit"] > 5
        return _response([
            {"date": "2026-11-20", "value": "."},
            {"date": "2026-11-19", "value": ""},
            {"date": "2026-11-18", "value": "17.5"},
        ])

    monkeypatch.setattr("runtime.data.fetch.fetch_pulse.get_with_retry", fake_get)
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_pulse.get_secret", lambda _key: "test-key"
    )
    pulse = fetch_pulse()
    assert pulse["status"] == "success"
    assert pulse["errors"] == []
    assert set(pulse["dates"].values()) == {"2026-11-18"}
    assert all(value == 17.5 for value in pulse["data"].values())

    monkeypatch.setattr("runtime.data.fetch.fetch_markets.get_with_retry", fake_get)
    monkeypatch.setattr(
        "runtime.data.fetch.fetch_markets.get_secret", lambda _key: "test-key"
    )
    dxy = _fetch_dxy_from_fred()
    assert dxy == {"close": 17.5, "date": "2026-11-18"}


def test_september_inflation_keeps_the_published_score_and_the_formula():
    """The fix does not move endpoints, weights, or the September rate."""
    rate = inflation_rate_from_levels(336.298, 324.245)
    assert rate == ((336.298 - 324.245) / 324.245) * 100
    assert METRIC_RANGES["inflation_rate"] == (-10, 15)
    assert WEIGHTS["inflation_rate"] == 0.15
    assert sum(WEIGHTS.values()) == 0.72
    payload = {
        "inflation_rate": {"data": {"inflation_rate": rate}},
        "incident_rate": {"data": {"incident_rate": 2443.27}},
        "unemployment_rate": {"data": {"unemployment_rate": 4.1}},
        "debt_to_gdp_ratio": {"data": {"debt_to_gdp_ratio": 121.18773}},
        "homelessness_rate": {"data": {"homelessness_rate": 0.22}},
        "trust_in_government": {"data": {"trust_in_government": 39.0}},
    }
    assert compute_index(payload)["index"] == 57.38
    without_inflation = {
        metric: body for metric, body in payload.items() if metric != "inflation_rate"
    }
    assert compute_index(without_inflation)["index"] == 60.6
