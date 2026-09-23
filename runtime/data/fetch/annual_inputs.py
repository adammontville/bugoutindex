# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Load one row from the annual manual-input table.

The weekly job calls this. It copies the cells a person wrote. It does not
fill a missing row, and it does not stamp the current time.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = _HERE.parent / "annual_inputs.csv"

COLUMNS = (
    "metric",
    "value",
    "observation_period",
    "observation_date",
    "source",
    "source_url",
    "reviewed_at",
)

# observation_date shape. Homelessness is a HUD reference date.
# Trust is the Edelman survey year and must not grow a month or day.
OBSERVATION_KIND = {
    "homelessness_rate": "hud_date",
    "trust_in_government": "edelman_year",
}

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_YEAR = re.compile(r"\d{4}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_FAKE_TIMESTAMPS = {
    "2025-01-01T00:00:00Z",
    "2025-01-01T00:00:00+00:00",
}


class AnnualInputError(Exception):
    """The annual table cannot supply this metric. Callers fail closed."""


def load_annual_row(metric: str, path: Path | None = None) -> dict:
    """Return the checklist row for ``metric``.

    ``value`` is a float. Every other field is the stripped cell text.
    A missing or malformed row raises ``AnnualInputError``.
    """
    table = Path(path) if path is not None else DEFAULT_TABLE
    rows = _read_rows(table)
    matched = [row for row in rows if (row.get("metric") or "").strip() == metric]
    if not matched:
        raise AnnualInputError(f"annual inputs table has no {metric} row")
    if len(matched) > 1:
        raise AnnualInputError(f"annual inputs table has more than one {metric} row")
    return _validate(metric, matched[0])


def _read_rows(table: Path) -> list:
    if not table.is_file():
        raise AnnualInputError(f"annual inputs table is missing: {table.name}")
    try:
        with table.open(newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
            missing = [name for name in COLUMNS if name not in header]
            if missing:
                raise AnnualInputError(
                    "annual inputs table is missing columns: " + ", ".join(missing)
                )
            return list(reader)
    except AnnualInputError:
        raise
    except OSError as exc:
        raise AnnualInputError(f"annual inputs table could not be read: {exc}") from exc


def _validate(metric: str, row: dict) -> dict:
    cleaned = {name: (row.get(name) or "").strip() for name in COLUMNS}
    for name in ("value", "observation_date", "reviewed_at"):
        text = cleaned[name]
        if text in _FAKE_TIMESTAMPS or "T" in text:
            raise AnnualInputError(
                f"annual inputs {name} for {metric} must be a date or year a person wrote, not a timestamp"
            )

    kind = OBSERVATION_KIND.get(metric)
    if kind is None:
        raise AnnualInputError(f"annual inputs table has no rules for {metric}")

    if not _NUMBER.fullmatch(cleaned["value"]):
        raise AnnualInputError(f"annual inputs value for {metric} is missing or not a number")

    if not cleaned["observation_period"]:
        raise AnnualInputError(f"annual inputs observation_period for {metric} is blank")

    observation = cleaned["observation_date"]
    if kind == "hud_date":
        if not _is_day(observation):
            raise AnnualInputError(
                f"annual inputs observation_date for {metric} must be the HUD reference date (YYYY-MM-DD)"
            )
    elif kind == "edelman_year":
        if not _YEAR.fullmatch(observation):
            raise AnnualInputError(
                f"annual inputs observation_date for {metric} must be the Edelman survey year (YYYY)"
            )
    if not cleaned["source"]:
        raise AnnualInputError(f"annual inputs source for {metric} is blank")
    url = cleaned["source_url"]
    if url and not url.startswith(("https://", "http://")):
        raise AnnualInputError(f"annual inputs source_url for {metric} is not a URL")

    reviewed = cleaned["reviewed_at"]
    if not _is_day(reviewed):
        raise AnnualInputError(
            f"annual inputs reviewed_at for {metric} must be the calendar date of the review (YYYY-MM-DD)"
        )

    return {
        "metric": metric,
        "value": float(cleaned["value"]),
        "observation_period": cleaned["observation_period"],
        "observation_date": observation,
        "source": cleaned["source"],
        "source_url": url,
        "reviewed_at": reviewed,
    }


def _is_day(text: str) -> bool:
    if not _DAY.fullmatch(text):
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return True
