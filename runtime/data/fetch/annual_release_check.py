# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Warn when the next HUD AHAR or Edelman release is past its expected window.

The clock is the source's release timing, not the age of the observation.
A HUD AHAR describes a January point-in-time night and usually appears 12 to
18 months later. Edelman publishes each January for that survey year. A
warning fires only after the next report's window, plus the grace period in
``RELEASE_WINDOWS``, has passed.

The weekly publisher does not import this module. ``compute_index`` does not
import it. A warning is a string for a person to read. It does not edit
``annual_inputs.csv`` and it does not change a score.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

# Usual publication lag, then a grace period after the late end of that window.
# A warning starts the day after ``grace_months`` past the late end.
RELEASE_WINDOWS = {
    "homelessness_rate": {
        "label": "HUD AHAR",
        # Next count is the January after the checklist observation.
        # That report usually appears this many months after that January 1.
        "min_months_after_next_pit": 12,
        "max_months_after_next_pit": 18,
        "grace_months": 1,
    },
    "trust_in_government": {
        "label": "Edelman Trust Barometer",
        # Next report is this month of the year after the checklist year.
        "release_month": 1,
        "grace_months": 1,
    },
}

_YEAR = re.compile(r"\d{4}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def add_calendar_months(day: date, months: int) -> date:
    """Return ``day`` plus ``months``, clamping the day to the target month."""
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def _hud_year(observation_date: str) -> int:
    text = observation_date.strip()
    if not _DAY.fullmatch(text):
        raise ValueError("HUD observation_date must be YYYY-MM-DD")
    year_text, month_text, day_text = text.split("-")
    parsed = date(int(year_text), int(month_text), int(day_text))
    if parsed.isoformat() != text:
        raise ValueError("HUD observation_date must be YYYY-MM-DD")
    return parsed.year


def _edelman_year(observation_date: str) -> int:
    text = observation_date.strip()
    if not _YEAR.fullmatch(text):
        raise ValueError("Edelman observation_date must be a survey year (YYYY)")
    return int(text)


def release_due_date(metric: str, observation_date: str) -> date:
    """Last day the current cell is still on time.

    The day after this date, the next release is past its window plus grace.
    """
    window = RELEASE_WINDOWS.get(metric)
    if window is None:
        raise ValueError(f"no release window configured for {metric}")
    if metric == "homelessness_rate":
        next_january = date(_hud_year(observation_date) + 1, 1, 1)
        late_months = window["max_months_after_next_pit"] + window["grace_months"]
        return add_calendar_months(next_january, late_months)
    next_year = _edelman_year(observation_date) + 1
    release_month = window["release_month"]
    window_end = date(next_year, release_month, calendar.monthrange(next_year, release_month)[1])
    return add_calendar_months(window_end, window["grace_months"])


def release_age_warning(
    *,
    metric: str,
    observation_date: str,
    as_of: date,
) -> str | None:
    """Return a warning when ``as_of`` is past the next release's window and grace.

    ``None`` means that next release is not yet overdue. The return value is
    never a substitute raw input.
    """
    window = RELEASE_WINDOWS[metric]
    due = release_due_date(metric, observation_date)
    if as_of <= due:
        return None
    overdue = due + timedelta(days=1)
    if metric == "homelessness_rate":
        next_year = _hud_year(observation_date) + 1
        span = (
            f"{window['min_months_after_next_pit']}–"
            f"{window['max_months_after_next_pit']} months after the "
            f"January {next_year} point-in-time count"
        )
    else:
        span = f"January {_edelman_year(observation_date) + 1}"
    return (
        f"{metric} still records {observation_date}. The next {window['label']} "
        f"was expected by {due.isoformat()} ({span}, plus "
        f"{window['grace_months']} month of grace). A newer release may be "
        f"overdue as of {overdue.isoformat()}. This check does not change the scored value."
    )
