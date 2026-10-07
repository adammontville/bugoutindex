# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Toronto overnight shelter census, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. HUD AHAR stays the annual national homelessness anchor. This
companion is the City of Toronto shelter system only. It is not a U.S.
figure, not a Canadian national figure, and not a substitute for that anchor.

Source: City of Toronto Open Data, "Daily Shelter & Overnight Service
Occupancy & Capacity". Verified 2026-10-07. The current datastore resource
is the one named "Daily shelter overnight occupancy" (resource
``42714176-4f05-44e6-b157-2b57f29b856a`` on that date). Year-stamped archive
files are not read. The resource id is looked up by that name on each fetch
so a later id change still follows the current file.

Each row is one program on one occupancy date. The stored series sums
``SERVICE_USER_COUNT`` across programs for that date. That is the city's
published program-level headcount. It is not a deduplicated count of people:
someone reported in two programs the same night is counted twice. Null
counts are skipped. The observation date is ``OCCUPANCY_DATE``. This module
does not stamp the clock.
"""
from __future__ import annotations

from typing import Dict, List

from runtime.data.fetch.shelter_shadow_common import assemble as _assemble
from runtime.data.fetch.shelter_shadow_common import valid_day, whole_count
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.redact import redact_secrets

PACKAGE_ID = "daily-shelter-overnight-service-occupancy-capacity"
PACKAGE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
DATASTORE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"
SOURCE_URL = "https://open.toronto.ca/dataset/daily-shelter-overnight-service-occupancy-capacity/"
# The live file, not a year archive. The id is resolved by this name.
RESOURCE_NAME = "Daily shelter overnight occupancy"
DATE_FIELD = "OCCUPANCY_DATE"
FIELD = "SERVICE_USER_COUNT"
SERIES = {
    "toronto_shelter_service_users": FIELD,
}
TRAILING_OBSERVATIONS = 90
PAGE_SIZE = 5000
MAX_PAGES = 12
TIMEOUT = 40
GEOGRAPHY = "Toronto, Ontario"
SCOPE = "Toronto only; not a U.S. figure and not the HUD AHAR rate"


def parse_rows(raw_rows: list) -> List[dict]:
    """Daily sums of program service-user counts.

    Null and non-numeric counts are skipped. A date with no numeric counts
    is dropped. At most ``TRAILING_OBSERVATIONS`` points are kept.
    """
    totals: Dict[str, int] = {}
    for row in raw_rows or []:
        if not isinstance(row, dict):
            continue
        day = valid_day(row.get(DATE_FIELD))
        count = whole_count(row.get(FIELD))
        if day is None or count is None:
            continue
        totals[day] = totals.get(day, 0) + count
    points = [{"date": day, "value": totals[day]} for day in sorted(totals)]
    if len(points) > TRAILING_OBSERVATIONS:
        points = points[-TRAILING_OBSERVATIONS:]
    return points


def assemble(parsed: Dict[str, list], errors: List[str], message: str = "") -> dict:
    """Public payload. ``in_bugout_index`` is always false."""
    return _assemble(
        SERIES,
        parsed,
        errors,
        geography=GEOGRAPHY,
        scope=SCOPE,
        dataset_id=PACKAGE_ID,
        source_url=SOURCE_URL,
        reading=(
            "sum of SERVICE_USER_COUNT across Toronto overnight programs "
            "on the occupancy date; not a deduplicated person count"
        ),
        message=message,
    )


def _resource_id() -> str:
    resp = get_with_retry(PACKAGE_URL, params={"id": PACKAGE_ID}, timeout=TIMEOUT)
    payload = resp.json()
    if not isinstance(payload, dict) or not payload.get("success"):
        raise ValueError("Toronto Open Data package lookup failed")
    resources = (payload.get("result") or {}).get("resources") or []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        if resource.get("name") == RESOURCE_NAME and resource.get("datastore_active"):
            resource_id = resource.get("id")
            if resource_id:
                return str(resource_id)
    raise ValueError("Toronto current occupancy resource was not found")


def _raw_rows() -> list:
    resource_id = _resource_id()
    rows: list = []
    offset = 0
    for _page in range(MAX_PAGES):
        resp = get_with_retry(
            DATASTORE_URL,
            params={
                "resource_id": resource_id,
                "limit": PAGE_SIZE,
                "offset": offset,
                "fields": f"{DATE_FIELD},{FIELD}",
            },
            timeout=TIMEOUT,
        )
        payload = resp.json()
        if not isinstance(payload, dict) or not payload.get("success"):
            raise ValueError("Toronto Open Data response was not a datastore page")
        records = (payload.get("result") or {}).get("records") or []
        if not isinstance(records, list):
            raise ValueError("Toronto Open Data records were not a list")
        rows.extend(records)
        if len(records) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE
    raise ValueError("Toronto Open Data page limit exceeded")


def fetch() -> dict:
    parsed: Dict[str, list] = {}
    errors: List[str] = []
    name = next(iter(SERIES))
    try:
        parsed[name] = parse_rows(_raw_rows())
        if not parsed[name]:
            errors.append(f"{name}: no observations")
    except RetryError as exc:
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: Toronto Open Data unreachable: {exc}"))
    except Exception as exc:  # noqa: BLE001
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: {exc}"))
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
