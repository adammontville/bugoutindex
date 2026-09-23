# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Annual checklist rows stay the published inputs and fail closed."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from runtime.data.fetch.annual_inputs import AnnualInputError, load_annual_row
from runtime.data.fetch.fetch_homelessness_rate import fetch as fetch_homelessness
from runtime.data.fetch.fetch_trust_in_government import fetch as fetch_trust
from runtime.processing.formula import compute_index

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "runtime" / "data" / "annual_inputs.csv"
FETCH_DIR = ROOT / "runtime" / "data" / "fetch"

# 19 September 2026 raw inputs, aside from the two checklist metrics.
LOCKED_OTHER_RAWS = {
    "inflation_rate": 3.353016322755652,
    "incident_rate": 2723.0,
    "unemployment_rate": 4.1,
    "debt_to_gdp_ratio": 122.59387,
}

HEADER = (
    "metric,value,observation_period,observation_date,source,source_url,reviewed_at\n"
)
HOMELESS_ROW = (
    "homelessness_rate,0.23,January 2024 point-in-time count,2024-01-01,"
    "2024 HUD AHAR,https://www.huduser.gov/portal/sites/default/files/pdf/2024-AHAR-Part-1.pdf,"
    "2025-03-13\n"
)
TRUST_ROW = (
    "trust_in_government,41,2025,2025,2025 Edelman Trust Barometer US Government,"
    "https://www.edelman.com/trust-barometer,2025-03-13\n"
)


def _write_table(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "annual_inputs.csv"
    path.write_text(HEADER + body)
    return path


def _assert_no_invented_timestamp(payload: dict) -> None:
    text = json.dumps(payload)
    assert "2025-01-01T00:00:00Z" not in text
    assert "T00:00:00" not in text
    assert payload.get("fetched_at") != date.today().isoformat()


def test_published_checklist_values_still_score_57_11():
    homelessness = fetch_homelessness()
    trust = fetch_trust()
    assert homelessness["status"] == "success"
    assert trust["status"] == "success"
    assert homelessness["data"]["homelessness_rate"] == 0.23
    assert trust["data"]["trust_in_government"] == 41.0

    assert homelessness["fetched_at"] is None
    assert homelessness["provenance"]["reference_date"] == "2024-01-01"
    assert homelessness["provenance"]["observation_period"] == "January 2024 point-in-time count"
    assert homelessness["provenance"]["last_set"] == "2024 HUD AHAR"
    assert homelessness["provenance"]["reviewed_at"] == "2025-03-13"
    assert homelessness["provenance"]["kind"] == "manual"

    assert trust["fetched_at"] == "2025"
    assert trust["provenance"]["year"] == "2025"
    assert trust["provenance"]["kind"] == "annual"
    assert trust["provenance"]["reviewed_at"] == "2025-03-13"
    assert "2025-01-01" not in trust["fetched_at"]

    _assert_no_invented_timestamp(homelessness)
    _assert_no_invented_timestamp(trust)

    raws = {
        **LOCKED_OTHER_RAWS,
        "homelessness_rate": homelessness["data"]["homelessness_rate"],
        "trust_in_government": trust["data"]["trust_in_government"],
    }
    payload = {metric: {"data": {metric: value}} for metric, value in raws.items()}
    assert compute_index(payload)["index"] == 57.11
    assert raws["incident_rate"] == 2723.0


def test_fetcher_review_dates_match_the_table_and_are_not_today():
    for metric, fetch in (
        ("homelessness_rate", fetch_homelessness),
        ("trust_in_government", fetch_trust),
    ):
        row = load_annual_row(metric)
        result = fetch()
        assert row["reviewed_at"] == "2025-03-13"
        assert result["provenance"]["reviewed_at"] == row["reviewed_at"]
        assert row["reviewed_at"] != date.today().isoformat()


def test_fetchers_do_not_call_the_clock():
    for name in ("annual_inputs.py", "fetch_homelessness_rate.py", "fetch_trust_in_government.py"):
        text = (FETCH_DIR / name).read_text()
        assert "datetime.now" not in text
        assert "date.today" not in text
        assert "utcnow" not in text
    for name in ("fetch_homelessness_rate.py", "fetch_trust_in_government.py"):
        assert "2025-01-01T00:00:00Z" not in (FETCH_DIR / name).read_text()
    loader = (FETCH_DIR / "annual_inputs.py").read_text()
    assert loader.count("2025-01-01T00:00:00Z") == 1
    assert "_FAKE_TIMESTAMPS" in loader


def test_missing_table_fails_closed(tmp_path: Path):
    missing = tmp_path / "absent.csv"
    for metric in ("homelessness_rate", "trust_in_government"):
        try:
            load_annual_row(metric, path=missing)
        except AnnualInputError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError(metric)


def test_missing_row_fails_closed(tmp_path: Path, monkeypatch):
    path = _write_table(tmp_path, TRUST_ROW)
    monkeypatch.setattr(
        "runtime.data.fetch.annual_inputs.DEFAULT_TABLE",
        path,
    )
    result = fetch_homelessness()
    assert result["status"] == "error"
    assert result["fetched_at"] is None
    assert result["data"] == {}
    assert "provenance" not in result
    _assert_no_invented_timestamp(result)


def test_malformed_rows_fail_closed(tmp_path: Path):
    cases = {
        "blank value": HOMELESS_ROW.replace(",0.23,", ",,", 1),
        "trust month-day": TRUST_ROW.replace(",2025,2025,", ",2025,2025-01-01,", 1),
        "fake reviewed_at": TRUST_ROW.replace(",2025-03-13\n", ",2025-01-01T00:00:00Z\n"),
        "blank reviewed_at": HOMELESS_ROW.replace(",2025-03-13\n", ",\n"),
        "impossible review date": HOMELESS_ROW.replace(",2025-03-13\n", ",2025-13-40\n"),
        "blank source": HOMELESS_ROW.replace(",2024 HUD AHAR,", ",,", 1),
        "hud year only": HOMELESS_ROW.replace(",2024-01-01,", ",2024,", 1),
    }
    for label, body in cases.items():
        path = _write_table(tmp_path, body)
        metric = "trust_in_government" if "trust" in label or "fake" in label else "homelessness_rate"
        try:
            load_annual_row(metric, path=path)
        except AnnualInputError:
            continue
        raise AssertionError(label)


def test_fetcher_passes_loader_errors_through_without_a_date(monkeypatch):
    def boom(metric, path=None):
        raise AnnualInputError("annual inputs table has no trust_in_government row")

    monkeypatch.setattr("runtime.data.fetch.fetch_trust_in_government.load_annual_row", boom)
    result = fetch_trust()
    assert result == {
        "status": "error",
        "message": "annual inputs table has no trust_in_government row",
        "fetched_at": None,
        "data": {},
    }
