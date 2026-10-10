# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""A release can be overdue. The check cannot change the score."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from runtime.data.fetch.annual_release_check import (
    RELEASE_WINDOWS,
    release_age_warning,
    release_due_date,
)
from runtime.data.fetch.fetch_homelessness_rate import fetch as fetch_homelessness
from runtime.data.fetch.fetch_trust_in_government import fetch as fetch_trust
from runtime.processing.formula import compute_index, interpret

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
FORMULA = ROOT / "runtime" / "processing" / "formula.py"
WEEKLY = ROOT / "runtime" / "publish" / "weekly_run.py"

# Other four inputs from the published 2026-10-09 basket. Homelessness and
# trust on that file stay the prior cells; this test substitutes the checklist.
BASKET_DATE = "2026-10-09"
AS_OF = date(2026, 10, 10)


def _basket_with_checklist() -> dict:
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    assert latest["publication_date"] == BASKET_DATE
    assert latest["methodology_version"] == "1.1.0"
    raws = {
        metric: latest["metrics"][metric]["raw"]
        for metric in (
            "inflation_rate",
            "incident_rate",
            "unemployment_rate",
            "debt_to_gdp_ratio",
            "homelessness_rate",
            "trust_in_government",
        )
    }
    assert raws["homelessness_rate"] == 0.23
    assert raws["trust_in_government"] == 41.0
    homelessness = fetch_homelessness()
    trust = fetch_trust()
    raws["homelessness_rate"] = homelessness["data"]["homelessness_rate"]
    raws["trust_in_government"] = trust["data"]["trust_in_government"]
    return raws


def _score(raws: dict) -> dict:
    payload = {metric: {"data": {metric: value}} for metric, value in raws.items()}
    return compute_index(payload)


def test_windows_are_the_source_calendars():
    hud = RELEASE_WINDOWS["homelessness_rate"]
    assert (hud["min_months_after_next_pit"], hud["max_months_after_next_pit"]) == (12, 18)
    assert hud["grace_months"] == 1
    edelman = RELEASE_WINDOWS["trust_in_government"]
    assert edelman["release_month"] == 1
    assert edelman["grace_months"] == 1
    # 2025 AHAR: next count is January 2026, due 18 months later plus 1 month.
    assert release_due_date("homelessness_rate", "2025-01-01") == date(2027, 8, 1)
    # Edelman 2026: next report is January 2027, then one month of grace.
    assert release_due_date("trust_in_government", "2026") == date(2027, 2, 28)


def test_current_cells_do_not_warn_on_2026_10_10():
    hud = release_age_warning(
        metric="homelessness_rate",
        observation_date="2025-01-01",
        as_of=AS_OF,
    )
    trust = release_age_warning(
        metric="trust_in_government",
        observation_date="2026",
        as_of=AS_OF,
    )
    assert hud is None
    assert trust is None
    assert fetch_homelessness()["observation_date"] == "2025-01-01"
    assert fetch_trust()["observation_date"] == "2026"


def test_hud_warns_only_after_the_next_ahar_window():
    # The 2024 cell on this date is past the January 2025 count's window.
    late = release_age_warning(
        metric="homelessness_rate",
        observation_date="2024-01-01",
        as_of=AS_OF,
    )
    assert late is not None
    assert "2026-08-01" in late
    assert "does not change the scored value" in late
    assert "0.22" not in late
    assert "0.23" not in late

    # Inside the 12–18 month span for that January 2025 count: still quiet.
    assert (
        release_age_warning(
            metric="homelessness_rate",
            observation_date="2024-01-01",
            as_of=date(2026, 5, 29),
        )
        is None
    )
    # Due date itself is still on time. The next day warns.
    assert (
        release_age_warning(
            metric="homelessness_rate",
            observation_date="2025-01-01",
            as_of=date(2027, 8, 1),
        )
        is None
    )
    overdue = release_age_warning(
        metric="homelessness_rate",
        observation_date="2025-01-01",
        as_of=date(2027, 8, 2),
    )
    assert overdue is not None
    assert "January 2026" in overdue


def test_edelman_warns_only_after_the_next_january():
    # Still holding 2025 in October 2026: the January 2026 report is overdue.
    late = release_age_warning(
        metric="trust_in_government",
        observation_date="2025",
        as_of=AS_OF,
    )
    assert late is not None
    assert "2026-02-28" in late
    assert "does not change the scored value" in late
    assert "39" not in late
    assert "41" not in late

    # January of the release year, and the grace month, stay quiet.
    assert (
        release_age_warning(
            metric="trust_in_government",
            observation_date="2025",
            as_of=date(2026, 1, 31),
        )
        is None
    )
    assert (
        release_age_warning(
            metric="trust_in_government",
            observation_date="2026",
            as_of=date(2027, 2, 28),
        )
        is None
    )
    overdue = release_age_warning(
        metric="trust_in_government",
        observation_date="2026",
        as_of=date(2027, 3, 1),
    )
    assert overdue is not None
    assert "January 2027" in overdue


def test_warning_does_not_change_the_2026_10_09_score():
    raws = _basket_with_checklist()
    assert raws["homelessness_rate"] == 0.22
    assert raws["trust_in_government"] == 39.0
    before = _score(raws)
    hud = release_age_warning(
        metric="homelessness_rate",
        observation_date=fetch_homelessness()["observation_date"],
        as_of=AS_OF,
    )
    trust = release_age_warning(
        metric="trust_in_government",
        observation_date=fetch_trust()["observation_date"],
        as_of=AS_OF,
    )
    assert hud is None
    assert trust is None
    after = _score(raws)
    assert after == before
    assert before["index"] == 57.50
    assert interpret(before["index"])["band"] == "Moderate Stability"
    formula = FORMULA.read_text(encoding="utf-8")
    weekly = WEEKLY.read_text(encoding="utf-8")
    assert "annual_release_check" not in formula
    assert "annual_release_check" not in weekly
    assert "release_age_warning" not in formula
    assert "release_due_date" not in formula
