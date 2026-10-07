# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
San Francisco shelter occupancy rate, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. HUD AHAR stays the annual national homelessness anchor. This
companion is San Francisco only. It is not a U.S. rate and it is not a
substitute for that anchor. It is also not a headcount: the city publishes
an average occupancy rate, not a census of people.

Source: DataSF Scorecard Measures ``kc49-udxn``, measure ``279``,
"Average occupancy rate within all year-round temporary shelter or crisis
intervention programs." Department of Homelessness and Supportive Housing.
Verified 2026-10-07. The API host is ``data.sf.gov`` (``data.sfgov.org``
redirects there). The source stores ``actual`` as a ratio (``0.91`` means
91 percent). This module stores percent points. Rows with a blank
``actual`` are dropped. The observation date is ``calendar_month`` reduced
to a calendar day (the month-end date the scorecard prints). This module
does not stamp the clock and does not use ``data_as_of``.

Measure ``7274`` (bed inventory) is a capacity count, not people in
shelter, and is not read.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from runtime.data.fetch.shelter_shadow_common import assemble as _assemble
from runtime.data.fetch.shelter_shadow_common import valid_day
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.redact import redact_secrets

DATASET_ID = "kc49-udxn"
MEASURE_CODE = "279"
SODA_URL = "https://data.sf.gov/resource/kc49-udxn.json"
SOURCE_URL = "https://data.sf.gov/City-Management-and-Ethics/Scorecard-Measures/kc49-udxn"
DATE_FIELD = "calendar_month"
FIELD = "actual"
SERIES = {
    "sf_shelter_occupancy_rate": MEASURE_CODE,
}
TRAILING_OBSERVATIONS = 24
TIMEOUT = 20
GEOGRAPHY = "San Francisco"
SCOPE = (
    "San Francisco only; an occupancy rate, not a headcount, "
    "not a U.S. figure, and not the HUD AHAR rate"
)


def percent_points(value: object) -> Optional[float]:
    """Ratio ``0.91`` to percent points ``91.0``, or None.

    Values above 1.5 are rejected. A later file that stores ``90`` instead
    of ``0.90`` fails closed instead of printing 9000 percent.
    """
    if value in ("", None, "."):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None
    if number < 0 or number > Decimal("1.5"):
        return None
    points = (number * 100).quantize(Decimal("0.1"))
    return float(points)


def parse_rows(raw_rows: list) -> List[dict]:
    """Monthly occupancy rates. Blank actuals are dropped.

    The returned dates are scorecard month-end dates, not a fetch time.
    At most ``TRAILING_OBSERVATIONS`` points are kept (the newest ones).
    """
    collapsed: Dict[str, float] = {}
    for row in raw_rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("measure_code") or MEASURE_CODE) not in ("", MEASURE_CODE):
            continue
        day = valid_day(row.get(DATE_FIELD))
        rate = percent_points(row.get(FIELD))
        if day is None or rate is None or day in collapsed:
            continue
        collapsed[day] = rate
    points = [{"date": day, "value": collapsed[day]} for day in sorted(collapsed)]
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
        dataset_id=DATASET_ID,
        source_url=SOURCE_URL,
        reading=(
            "average occupancy rate of San Francisco year-round temporary "
            "shelter and crisis intervention programs, in percent"
        ),
        message=message,
        extra={"unit": "percent", "measure_code": MEASURE_CODE},
    )


def _raw_rows() -> list:
    params = {
        "$select": f"measure_code,{DATE_FIELD},{FIELD}",
        "$where": f"measure_code='{MEASURE_CODE}' AND actual IS NOT NULL",
        "$order": f"{DATE_FIELD} DESC",
        "$limit": TRAILING_OBSERVATIONS + 6,
    }
    resp = get_with_retry(SODA_URL, params=params, timeout=TIMEOUT)
    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError("DataSF response was not a list")
    return payload


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
        errors.append(redact_secrets(f"{name}: DataSF unreachable: {exc}"))
    except Exception as exc:  # noqa: BLE001
        parsed[name] = []
        errors.append(redact_secrets(f"{name}: {exc}"))
    return assemble(parsed, errors)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
