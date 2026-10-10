# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Warn when a HUD or Edelman observation is old enough that a newer release could exist.

The weekly publisher does not import this module. ``compute_index`` does not
import it. A warning is a string for a person to read. It does not edit
``annual_inputs.csv`` and it does not change a score.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime

# About 13 months. A warning fires only after the observation anchor plus
# this many calendar months, so an observation that is exactly 13 months
# old does not warn yet.
RELEASE_AGE_MONTHS = 13

_YEAR = re.compile(r"\d{4}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def add_calendar_months(day: date, months: int) -> date:
    """Return ``day`` plus ``months``, clamping the day to the target month."""
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def observation_anchor(observation_date: str) -> date:
    """Calendar day used to age an annual observation.

    A HUD reference date is that ``YYYY-MM-DD``. An Edelman survey year is
    January 1 of that year, so a January release is not flagged in the same
    month it comes out.
    """
    text = observation_date.strip()
    if _YEAR.fullmatch(text):
        return date(int(text), 1, 1)
    if _DAY.fullmatch(text):
        return datetime.strptime(text, "%Y-%m-%d").date()
    raise ValueError(
        "observation_date must be a HUD date (YYYY-MM-DD) or an Edelman year (YYYY)"
    )


def release_age_warning(
    *,
    metric: str,
    observation_date: str,
    as_of: date,
) -> str | None:
    """Return a warning when ``as_of`` is more than 13 months after the observation.

    ``None`` means the observation is not yet that old. The return value is
    never a substitute raw input.
    """
    anchor = observation_anchor(observation_date)
    due = add_calendar_months(anchor, RELEASE_AGE_MONTHS)
    if as_of <= due:
        return None
    return (
        f"{metric} observation {observation_date} is more than {RELEASE_AGE_MONTHS} "
        f"months before {as_of.isoformat()}. A newer HUD AHAR or Edelman Trust "
        "Barometer may exist. This check does not change the scored value."
    )
