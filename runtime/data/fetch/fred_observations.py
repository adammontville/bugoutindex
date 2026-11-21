# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""How FRED missing observations are read.

FRED encodes a period with no value as the string ``.``. An empty string
means the same thing. Neither is a number. Every FRED series this
repository fetches — core metrics, companions, and the dollar index —
drops those rows and keeps the latest real print.

Nothing in this module fills a gap. A missing month is not zero, not the
neighbor, and not an interpolated value.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

_DAY = re.compile(r"\d{4}-\d{2}-\d{2}$")

# Monthly and quarterly series. A handful of leading "." rows must not
# hide the latest real print.
LEVEL_OBSERVATION_LIMIT = 24
# Daily series. Weekends and holidays are ".".
DAILY_OBSERVATION_LIMIT = 30
# CPI year-over-year needs the comparison month and room to step back
# when that month is missing, including when the newest row itself is ".".
CPI_OBSERVATION_LIMIT = 48


def is_missing_fred_value(value: object) -> bool:
    """True for ``.``, empty text, and None. Numeric zero is a real print."""
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return False
    return str(value).strip() in {"", "."}


def observation_day(value: object) -> Optional[str]:
    """FRED observation date as ``YYYY-MM-DD``, or None."""
    if value is None:
        return None
    text = str(value).strip()
    day = text[:10]
    if _DAY.fullmatch(day) is None:
        return None
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return None
    return day


def parse_numeric_observations(raw_observations: list) -> list:
    """Chronological real prints, ``{"date", "value"}`` with a float value.

    ``.`` and empty values are dropped. Invalid dates and non-numeric text
    are dropped. Duplicate dates keep the last row. The list is not filled
    in for months FRED did not print.
    """
    if not isinstance(raw_observations, list):
        return []
    found: dict = {}
    for obs in raw_observations:
        if not isinstance(obs, dict):
            continue
        day = observation_day(obs.get("date", obs.get("observation_date")))
        if day is None:
            continue
        raw_value = obs.get("value")
        if is_missing_fred_value(raw_value):
            continue
        try:
            found[day] = float(str(raw_value).strip())
        except (TypeError, ValueError):
            continue
    return [{"date": day, "value": found[day]} for day in sorted(found)]
