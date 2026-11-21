# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Checks for the live weekly snapshot that do not pin its headline.

``docs/data/latest.json`` is replaced every Friday. Tests that need the
2026-10-09 basket, or any other published week, read that row from
``runtime/data/weekly_bugout_index.csv``.
"""
from __future__ import annotations

from runtime.data.fetch.fetch_incident_rate import (
    NATIONWIDE_RATE_TOLERANCE,
    RATE_SOURCE_NATIONWIDE,
    RATE_SOURCE_WEIGHTED,
)
from runtime.processing.formula import CORE_METRICS, compute_index, interpret
from runtime.publish.snapshot_schema import (
    ACCEPTED_METHODOLOGY_VERSIONS,
    METHODOLOGY_VERSION,
    SCHEMA_VERSION,
    validate_published_snapshot,
)


def assert_live_snapshot_matches_formula(latest: dict) -> None:
    """Schema 1, the current methodology stamp, and a headline ``compute_index`` produced.

    Methodology 1.1.1 is the stamp on new publishes. It scores the checklist
    cells: homelessness 0.22 (2025 AHAR, observed 2025-01-01) and trust 39
    (2026 Edelman, observed 2026). Those are not the 1.1.0 week's 0.23 and 41.

    Methodology 1.1.0, which 1.1.1 keeps, scores the RTCI Nationwide Full
    Sample when that row matches the population-weighted total of the other
    usable rows, and the weighted total otherwise. The unweighted agency mean
    stays a diagnostic (``candidate_incident_rate``). The 1.0.0 constant
    2723.0 stays a diagnostic (``v1_0_0_locked_incident_rate``). Neither is
    selected by ``rate_source``.

    The publication date and the index level move when FRED prints move.
    They are not pinned here. The headline has to equal the formula on the
    snapshot's own six raw values.
    """
    assert latest["schema_version"] == SCHEMA_VERSION == 1
    assert METHODOLOGY_VERSION == "1.1.1"
    assert ACCEPTED_METHODOLOGY_VERSIONS == ("1.0.0", "1.1.0", "1.1.1")
    assert latest["methodology_version"] == METHODOLOGY_VERSION
    assert validate_published_snapshot(latest) == []
    assert set(latest["metrics"]) == set(CORE_METRICS)

    raws = {metric: latest["metrics"][metric]["raw"] for metric in CORE_METRICS}
    scored = compute_index(
        {metric: {"data": {metric: value}} for metric, value in raws.items()}
    )
    assert latest["bugout_index"] == scored["index"]
    assert latest["interpretation"]["band"] == interpret(scored["index"])["band"]

    assert raws["homelessness_rate"] == 0.22
    assert latest["metrics"]["homelessness_rate"]["observation_date"] == "2025-01-01"
    assert raws["trust_in_government"] == 39.0
    assert latest["metrics"]["trust_in_government"]["observation_date"] == "2026"

    crime = latest["metrics"]["incident_rate"]
    diagnostics = crime["diagnostics"]
    assert diagnostics["index_input"] is True
    assert diagnostics["v1_0_0_locked_incident_rate"] == 2723.0
    assert crime["raw"] == diagnostics["scored_incident_rate"]
    assert diagnostics["candidate_incident_rate"] == diagnostics["latest_month_incident_rate"]
    assert diagnostics["candidate_month"] == diagnostics["latest_month"]
    assert crime["observation_date"] == crime["provenance"]["value_month_end"]
    assert crime["provenance"]["value_month"] == diagnostics["latest_month"]
    source = diagnostics["rate_source"]
    assert source in (RATE_SOURCE_NATIONWIDE, RATE_SOURCE_WEIGHTED)
    if source == RATE_SOURCE_NATIONWIDE:
        assert crime["raw"] == diagnostics["nationwide_full_sample_incident_rate"]
        weighted = diagnostics["population_weighted_excluding_nationwide"]
        if weighted is not None:
            assert abs(crime["raw"] - weighted) <= NATIONWIDE_RATE_TOLERANCE
    else:
        assert crime["raw"] == diagnostics["population_weighted_excluding_nationwide"]
        nationwide = diagnostics["nationwide_full_sample_incident_rate"]
        assert nationwide is None or nationwide != crime["raw"]
