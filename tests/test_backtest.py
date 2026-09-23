# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""v1.0.0 FRED replay: 57.11 lock, and no invented crime, homelessness, or trust."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from runtime.backtest.cli import main
from runtime.backtest.harness import (
    FRED_SERIES_ID,
    HELD_CONSTANT_BASELINE,
    OUTPUT_DIR,
    OUTPUT_FILES,
    SPARSE_METRICS,
    WINDOW_ORDER,
    WINDOWS,
    FredLevels,
    build_replay,
    compute_index,
    cpi_yoy,
    csv_fields,
    fetch_fred_levels,
    iter_months,
    load_fixtures,
    load_published_raws,
    parse_observations,
    prior_year_date,
    replay_date,
    score_published_inputs,
)
from runtime.data.fetch.fetch_debt_to_gdp_ratio import SERIES_ID as DEBT_SERIES_ID
from runtime.data.fetch.fetch_inflation_rate import SERIES_ID as CPI_SERIES_ID
from runtime.data.fetch.fetch_unemployment_rate import SERIES_ID as UNEMPLOYMENT_SERIES_ID
from runtime.processing.formula import CORE_METRICS, WEIGHTS
from runtime.processing.formula import compute_index as formula_compute_index
from runtime.processing.formula import interpret
from runtime.publish.weekly_run import compute_index as weekly_compute_index

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DATE = "2026-09-19"
FRED_WEIGHT = (
    WEIGHTS["inflation_rate"] + WEIGHTS["unemployment_rate"] + WEIGHTS["debt_to_gdp_ratio"]
)


def _published_payload(raws: dict) -> dict:
    return {metric: {"data": {metric: value}} for metric, value in raws.items()}


def _payload_from_row(row: dict) -> dict:
    payload = {}
    for metric in CORE_METRICS:
        value = row[metric]
        if value is None:
            continue
        payload[metric] = {"data": {metric: value}}
    return payload


def test_harness_reproduces_57_11_on_september_19_inputs():
    raws = load_published_raws()
    assert raws["incident_rate"] == 2723.0
    assert raws["homelessness_rate"] == 0.23
    assert raws["trust_in_government"] == 41.0
    assert HELD_CONSTANT_BASELINE["incident_rate"] == raws["incident_rate"]
    assert HELD_CONSTANT_BASELINE["homelessness_rate"] == raws["homelessness_rate"]
    assert HELD_CONSTANT_BASELINE["trust_in_government"] == raws["trust_in_government"]

    scored = score_published_inputs(raws)
    assert scored["index"] == 57.11
    assert interpret(scored["index"])["band"] == "Moderate Stability"
    assert compute_index is formula_compute_index
    assert weekly_compute_index(_published_payload(raws))["index"] == 57.11
    assert sum(WEIGHTS.values()) == 0.72


def test_locked_check_refuses_a_partial_snapshot():
    with pytest.raises(ValueError, match="all six published inputs"):
        score_published_inputs({"inflation_rate": 3.353016322755652})


def test_august_2026_fred_fixture_plus_held_baseline_is_57_11():
    """The recorded FRED vintage rebuilds the three published FRED inputs.

    Held crime, homelessness, and trust are the named baseline, not a history.
    Partial mode leaves them out, so it must not print 57.11.
    """
    raws = load_published_raws()
    levels = load_fixtures()
    held = replay_date(levels, "2026-08-01", "held_constant")

    assert held["inflation_rate"] == raws["inflation_rate"] == 3.353016322755652
    assert held["inflation_cpi_prior_date"] == "2025-08-01"
    assert held["unemployment_rate"] == raws["unemployment_rate"] == 4.1
    assert held["debt_to_gdp_ratio"] == raws["debt_to_gdp_ratio"] == 122.59387
    assert held["debt_to_gdp_ratio_status"] == "carried_forward"
    assert held["debt_to_gdp_ratio_observation_date"] == "2026-01-01"
    assert held["incident_rate"] == 2723.0
    assert held["incident_rate_status"] == "held_constant"
    assert held["homelessness_rate_status"] == "held_constant"
    assert held["trust_in_government_status"] == "held_constant"
    assert held["held_constant_baseline"] == "published_2026-09-19"
    assert held["replay_index"] == score_published_inputs(raws)["index"] == 57.11
    assert compute_index(_payload_from_row(held))["index"] == 57.11

    partial = replay_date(levels, "2026-08-01", "partial")
    assert partial["replay_index"] != 57.11
    assert partial["incident_rate"] is None
    assert partial["homelessness_rate"] is None
    assert partial["trust_in_government"] is None
    assert partial["inputs_present"] == "inflation_rate|unemployment_rate|debt_to_gdp_ratio"
    for metric in SPARSE_METRICS:
        assert partial[f"{metric}_status"] == "excluded"
        assert metric not in partial["inputs_present"].split("|")


def test_partial_and_held_constant_do_not_invent_sparse_history():
    levels = load_fixtures()
    partial_rows = build_replay(levels, WINDOW_ORDER, "partial")
    held_rows = build_replay(levels, WINDOW_ORDER, "held_constant")
    assert len(partial_rows) == 37
    assert [row["date"] for row in partial_rows] == [row["date"] for row in held_rows]

    for row in partial_rows:
        assert row["score_mode"] == "partial"
        assert row["inputs_held_constant"] == ""
        assert row["held_constant_baseline"] == ""
        assert "not historical observations" in row["score_note"]
        assert row["inputs_excluded"] == "incident_rate|homelessness_rate|trust_in_government"
        for metric in SPARSE_METRICS:
            assert row[metric] is None
            assert row[f"{metric}_status"] == "excluded"
        assert compute_index(_payload_from_row(row))["index"] == row["replay_index"]
        assert "incident_rate" not in _payload_from_row(row)

    for row in held_rows:
        assert row["score_mode"] == "held_constant"
        assert row["held_constant_baseline"] == "published_2026-09-19"
        assert row["inputs_held_constant"] == "incident_rate|homelessness_rate|trust_in_government"
        assert "held_constant" in row["score_note"]
        assert "not historical observations" in row["score_note"]
        for metric in SPARSE_METRICS:
            assert row[metric] == HELD_CONSTANT_BASELINE[metric]
            assert row[f"{metric}_status"] == "held_constant"
        assert compute_index(_payload_from_row(row))["index"] == row["replay_index"]
        assert row["replay_index"] != partial_rows[held_rows.index(row)]["replay_index"]


def test_crisis_windows_label_debt_carry_and_keep_the_three_fred_series():
    levels = load_fixtures()
    rows = {row["date"]: row for row in build_replay(levels, ("2008",), "partial")}
    assert list(rows)[0] == "2007-12-01"
    assert list(rows)[-1] == "2009-12-01"
    assert len(iter_months(WINDOWS["2008"].start, WINDOWS["2008"].end)) == 25
    assert len(iter_months(WINDOWS["2020"].start, WINDOWS["2020"].end)) == 12

    september = rows["2008-09-01"]
    assert september["debt_to_gdp_ratio_status"] == "carried_forward"
    assert september["debt_to_gdp_ratio_observation_date"] == "2008-07-01"
    assert september["debt_to_gdp_ratio"] == levels.debt_to_gdp["2008-07-01"] == 67.28455
    july = rows["2008-07-01"]
    assert july["debt_to_gdp_ratio_status"] == "observed"
    assert july["debt_to_gdp_ratio_observation_date"] == "2008-07-01"

    assert rows["2009-10-01"]["unemployment_rate"] == 10.0
    yoy = cpi_yoy(levels.cpi["2008-09-01"], levels.cpi["2007-09-01"])
    assert september["inflation_rate"] == yoy
    assert september["inflation_cpi_prior_date"] == prior_year_date("2008-09-01") == "2007-09-01"
    assert september["weight_denominator"] == FRED_WEIGHT == 0.39
    assert FRED_WEIGHT != sum(WEIGHTS.values())

    crisis = build_replay(levels, WINDOW_ORDER, "partial")
    assert {row["window"] for row in crisis} == {"2008", "2020"}
    assert all(row["date"] != "2026-08-01" for row in crisis)
    april = next(row for row in crisis if row["date"] == "2020-04-01")
    assert april["window"] == "2020"
    assert april["unemployment_rate"] == 14.8
    assert april["debt_to_gdp_ratio_status"] == "observed"
    assert april["debt_to_gdp_ratio"] == levels.debt_to_gdp["2020-04-01"] == 132.66287
    assert april["inflation_rate"] == cpi_yoy(levels.cpi["2020-04-01"], levels.cpi["2019-04-01"])
    assert april["methodology_version"] == "1.0.0"
    assert april["fred_download_date"] == "2026-09-23"
    assert april["replay_index"] == 45.51
    assert april["band"] == "Low Stability"

    held_april = next(
        row for row in build_replay(levels, ("2020",), "held_constant") if row["date"] == "2020-04-01"
    )
    assert held_april["weight_denominator"] == sum(WEIGHTS.values()) == 0.72
    assert held_april["incident_rate_status"] == "held_constant"
    assert held_april["replay_index"] == 51.67
    assert held_april["band"] == "Low Stability"


def test_partial_mode_shrinks_the_denominator_when_a_fred_input_is_missing():
    levels = FredLevels(
        cpi={"2019-05-01": 100.0},
        unemployment={"2020-05-01": 10.0},
        debt_to_gdp={},
    )
    may = next(row for row in build_replay(levels, ("2020",), "partial") if row["date"] == "2020-05-01")
    assert may["inflation_rate_status"] == "excluded"
    assert may["debt_to_gdp_ratio_status"] == "excluded"
    assert may["unemployment_rate"] == 10.0
    assert may["inputs_present"] == "unemployment_rate"
    assert may["weight_denominator"] == WEIGHTS["unemployment_rate"]
    expected = compute_index({"unemployment_rate": {"data": {"unemployment_rate": 10.0}}})
    assert may["replay_index"] == expected["index"]
    for metric in SPARSE_METRICS:
        assert may[metric] is None
        assert may[f"{metric}_status"] == "excluded"

    held = next(
        row for row in build_replay(levels, ("2020",), "held_constant") if row["date"] == "2020-05-01"
    )
    assert held["incident_rate"] == 2723.0
    assert held["incident_rate_status"] == "held_constant"
    present_weights = (
        WEIGHTS["unemployment_rate"]
        + WEIGHTS["incident_rate"]
        + WEIGHTS["homelessness_rate"]
        + WEIGHTS["trust_in_government"]
    )
    assert held["weight_denominator"] == present_weights
    assert held["replay_index"] == compute_index(_payload_from_row(held))["index"]
    assert "incident_rate" in held["inputs_present"].split("|")


def test_yoy_construction_matches_the_live_fetcher():
    source = (ROOT / "runtime" / "data" / "fetch" / "fetch_inflation_rate.py").read_text()
    assert "((current_cpi - previous_cpi) / previous_cpi) * 100" in source
    assert "str(int(current_date[:4]) - 1) + current_date[4:]" in source
    assert prior_year_date("2026-08-01") == "2025-08-01"
    assert cpi_yoy(334.131, 323.291) == ((334.131 - 323.291) / 323.291) * 100
    assert FRED_SERIES_ID == {
        "cpi": CPI_SERIES_ID,
        "unemployment": UNEMPLOYMENT_SERIES_ID,
        "debt_to_gdp": DEBT_SERIES_ID,
    }
    assert CPI_SERIES_ID == "CPIAUCSL"
    assert UNEMPLOYMENT_SERIES_ID == "UNRATE"
    assert DEBT_SERIES_ID == "GFDEGDQ188S"


def test_harness_does_not_keep_a_second_formula():
    source = (ROOT / "runtime" / "backtest" / "harness.py").read_text()
    assert "from runtime.processing.formula import" in source
    assert "def compute_index(" not in source
    assert "def normalize(" not in source
    assert "(-10, 15)" not in source
    assert "8000" not in source
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text()
    render = (ROOT / "runtime" / "publish" / "render.py").read_text()
    assert "runtime.backtest" not in weekly
    assert "runtime.backtest" not in render


def test_parse_observations_drops_placeholders():
    points = parse_observations([
        {"date": "2020-04-01", "value": "14.8"},
        {"date": "2020-05-01", "value": "."},
        {"date": "not-a-date", "value": "1"},
        {"observation_date": "2020-06-01", "value": ""},
    ])
    assert points == {"2020-04-01": 14.8}


def test_fred_fetch_asks_for_the_prior_year_and_not_the_latest_point_only():
    calls = []

    class Response:
        def __init__(self, series_id: str):
            self.series_id = series_id

        def json(self):
            if self.series_id == "CPIAUCSL":
                return {
                    "observations": [
                        {"date": "2019-01-01", "value": "100"},
                        {"date": "2020-01-01", "value": "102"},
                        {"date": "2020-02-01", "value": "."},
                    ]
                }
            if self.series_id == "UNRATE":
                return {"observations": [{"date": "2020-01-01", "value": "3.6"}]}
            return {"observations": [{"date": "2019-10-01", "value": "105.5"}]}

    def fake_get(url, params=None, **_kwargs):
        assert url.endswith("/fred/series/observations")
        calls.append(dict(params))
        return Response(params["series_id"])

    levels = fetch_fred_levels(("2020",), api_key="test-key", request=fake_get)
    assert levels.unemployment["2020-01-01"] == 3.6
    assert "2020-02-01" not in levels.cpi
    cpi_call = next(call for call in calls if call["series_id"] == "CPIAUCSL")
    assert cpi_call["observation_start"] == "2019-01-01"
    assert cpi_call["observation_end"] == "2020-12-01"
    assert cpi_call["api_key"] == "test-key"
    assert "limit" not in cpi_call


def test_fred_source_without_a_key_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("runtime.backtest.harness.get_secret", lambda _key: None)
    code = main(["--source", "fred", "--output", str(tmp_path), "--windows", "2020"])
    assert code == 2
    assert list(tmp_path.iterdir()) == []


def test_cli_writes_labeled_fixture_csv_and_prints_the_locked_score(tmp_path, capsys):
    code = main([
        "--source",
        "fixtures",
        "--mode",
        "both",
        "--windows",
        "2020",
        "--output",
        str(tmp_path),
        "--check-locked",
    ])
    assert code == 0
    printed = capsys.readouterr().out
    assert f"{PUBLISHED_DATE} 57.11 Moderate Stability methodology 1.0.0" in printed

    partial = list(csv.DictReader((tmp_path / "replay_partial.csv").open(encoding="utf-8")))
    held = list(csv.DictReader((tmp_path / "replay_held_constant.csv").open(encoding="utf-8")))
    assert [row["date"] for row in partial][0] == "2020-01-01"
    assert partial[-1]["date"] == "2020-12-01"
    assert all(row["incident_rate"] == "" for row in partial)
    assert all(row["homelessness_rate"] == "" for row in partial)
    assert all(row["trust_in_government"] == "" for row in partial)
    assert all(row["incident_rate_status"] == "excluded" for row in partial)
    assert all(row["incident_rate"] == "2723" for row in held)
    assert all(row["incident_rate_status"] == "held_constant" for row in held)
    assert all(row["homelessness_rate"] == "0.23" for row in held)
    assert all(row["trust_in_government"] == "41" for row in held)
    assert "2723" not in (tmp_path / "replay_partial.csv").read_text(encoding="utf-8")


def test_committed_tables_match_the_harness():
    levels = load_fixtures()
    for mode, filename in OUTPUT_FILES.items():
        fresh = [csv_fields(row) for row in build_replay(levels, WINDOW_ORDER, mode)]
        with (OUTPUT_DIR / filename).open(newline="", encoding="utf-8") as handle:
            committed = list(csv.DictReader(handle))
        assert committed == fresh
        assert {row["window"] for row in committed} == {"2008", "2020"}
        assert any(row["date"] == "2008-09-01" for row in committed)
        assert any(row["date"] == "2020-04-01" for row in committed)
