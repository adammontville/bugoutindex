# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""A stale annual observation can warn. It cannot change the score."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from runtime.data.fetch.annual_release_check import (
    RELEASE_AGE_MONTHS,
    release_age_warning,
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


def test_hud_warns_after_13_months_and_edelman_2026_does_not_yet():
    assert RELEASE_AGE_MONTHS == 13
    as_of = date(2026, 10, 10)
    hud = release_age_warning(
        metric="homelessness_rate",
        observation_date="2025-01-01",
        as_of=as_of,
    )
    assert hud is not None
    assert "does not change the scored value" in hud
    assert "0.22" not in hud

    # Exactly 13 calendar months later is not yet "more than" 13 months.
    assert (
        release_age_warning(
            metric="homelessness_rate",
            observation_date="2025-01-01",
            as_of=date(2026, 2, 1),
        )
        is None
    )
    assert (
        release_age_warning(
            metric="homelessness_rate",
            observation_date="2025-01-01",
            as_of=date(2026, 2, 2),
        )
        is not None
    )

    assert (
        release_age_warning(
            metric="trust_in_government",
            observation_date="2026",
            as_of=as_of,
        )
        is None
    )
    assert (
        release_age_warning(
            metric="trust_in_government",
            observation_date="2026",
            as_of=date(2027, 2, 1),
        )
        is None
    )
    later = release_age_warning(
        metric="trust_in_government",
        observation_date="2026",
        as_of=date(2027, 2, 2),
    )
    assert later is not None
    assert "39" not in later


def test_warning_does_not_change_the_2026_10_09_score():
    raws = _basket_with_checklist()
    assert raws["homelessness_rate"] == 0.22
    assert raws["trust_in_government"] == 39.0
    before = _score(raws)
    warning = release_age_warning(
        metric="homelessness_rate",
        observation_date=fetch_homelessness()["observation_date"],
        as_of=date(2026, 10, 10),
    )
    assert warning is not None
    after = _score(raws)
    assert after == before
    assert before["index"] == 57.50
    assert interpret(before["index"])["band"] == "Moderate Stability"
    assert "annual_release_check" not in FORMULA.read_text(encoding="utf-8")
    assert "annual_release_check" not in WEEKLY.read_text(encoding="utf-8")
    assert "release_age_warning" not in FORMULA.read_text(encoding="utf-8")
