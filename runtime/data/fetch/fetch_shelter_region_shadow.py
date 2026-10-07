# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
U.S. regional shelter checklist, shown beside the BugOut Index.

These series are not inputs. ``compute_index`` never reads them, and they
have no weight. HUD AHAR stays the scored national homelessness input.

The weekly job reads ``runtime/data/shelter_region_shadow.csv``. It does
not download Nashville PDFs, the Austin dashboard, or the Denver dashboard.
A person updates the checklist when a new cited figure is published.
See ``incubating/shelter_census_companions.md``.
"""
from __future__ import annotations

from pathlib import Path

from runtime.data.fetch.manual_checklist import ChecklistError, build_payload, load_series
from runtime.util.redact import redact_secrets

_HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = _HERE.parent / "shelter_region_shadow.csv"

SERIES = {
    "nashville_hmis_people": "people experiencing homelessness in the month",
    "austin_sheltered_people": "people likely experiencing sheltered homelessness",
    "denver_shelter_occupancy": "pilot shelter occupancy rate",
}
VALUE_KINDS = {
    "nashville_hmis_people": "count",
    "austin_sheltered_people": "count",
    "denver_shelter_occupancy": "percent",
}
MAX_ROWS = 24
_EXTRA = {
    "geography": "U.S. regional bellwethers",
    "scope": (
        "Local U.S. readings only. None is a U.S. total and none replaces HUD AHAR."
    ),
    "checklist": "runtime/data/shelter_region_shadow.csv",
    "cadence": "monthly when the publisher posts a new cited figure",
    "regions": {
        "nashville_hmis_people": "Southeast — Nashville–Davidson, Tennessee",
        "austin_sheltered_people": "South — Austin/Travis County, Texas",
        "denver_shelter_occupancy": "Southwest — Denver, Colorado",
    },
    "measures": {
        "nashville_hmis_people": (
            "People who experienced homelessness in Nashville-Davidson during the "
            "month, from the Metro Nashville Office of Homeless Services HMIS "
            "monthly report. The count covers participating HMIS providers "
            "(emergency shelter, transitional housing, street outreach, supportive "
            "services, and permanent housing). It is not a one-night shelter census. "
            "Nashville Rescue Mission rows on the same PDF are separate and are not "
            "added. Earlier months in this checklist were read from the chart on the "
            "July 2026 report."
        ),
        "austin_sheltered_people": (
            "People engaged in the Austin/Travis Homelessness Response System in "
            "the prior six months and likely experiencing sheltered homelessness, "
            "as printed on the ECHO HRS dashboard. Dashboard month June 2025, "
            "published September 10, 2025, data effective 2025-07-01. That lag is "
            "part of the reading. The references page defines a one-day sheltered "
            "snapshot, and that chart was not a readable number on the public pages "
            "when this row was entered."
        ),
        "denver_shelter_occupancy": (
            "Occupancy rate for the seven-shelter HOST performance-based contracting "
            "pilot (769 units) in Q2 2026, from the August 4, 2026 HOST release. "
            "Occupied rooms divided by available rooms. Not a count of distinct "
            "people and not the full Denver shelter system. The All In Mile High "
            "citywide dashboard is the monthly page to read next; this checklist "
            "stores the occupancy rate HOST published."
        ),
    },
    "index_pages": {
        "nashville_hmis_people": (
            "https://www.nashville.gov/departments/office-homeless-services/"
            "homeless-management-information-system/monthly-data-reports"
        ),
        "austin_sheltered_people": "https://echoatx.github.io/hrs-dashboard-site/",
        "denver_shelter_occupancy": (
            "https://www.denvergov.org/Government/Agencies-Departments-Offices/"
            "Agencies-Departments-Offices-Directory/Mayors-Office/Programs-and-Initiatives/"
            "Homelessness-Initiative/All-In-Mile-High-Dashboard"
        ),
    },
}


def fetch(path: Path | None = None) -> dict:
    """Return the checklist rows, or fail with no invented date."""
    table = Path(path) if path is not None else DEFAULT_TABLE
    try:
        points = load_series(
            table,
            required=SERIES,
            max_rows_per_series=MAX_ROWS,
            label="U.S. regional shelter",
            value_kinds=VALUE_KINDS,
        )
    except ChecklistError as exc:
        return build_payload(SERIES, {}, [redact_secrets(str(exc))], extra=_EXTRA)
    except Exception as exc:  # noqa: BLE001
        return build_payload(
            SERIES,
            {},
            [redact_secrets(f"U.S. regional shelter: {exc}")],
            extra=_EXTRA,
        )
    return build_payload(SERIES, points, [], extra=_EXTRA)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
