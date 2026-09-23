# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Source observation dates for the six core inputs.

The weekly CSV ``date`` column is the publication date. ``source_fetched_at``
is whatever the fetcher stored in ``fetched_at``. For the FRED series that
field is the observation date. For crime and homelessness it used to be a
placeholder timestamp, which is not an observation date.

``observation_date`` is the period the raw value describes:

* inflation, unemployment, debt-to-GDP — FRED observation date (``YYYY-MM-DD``)
* crime — last day of the file's value month
* homelessness — reference date of the point-in-time count
* trust — Edelman survey year (``YYYY``)

A later week can change the raw value and keep this date. That is a revision
of the same observation. A different date is a new observation period.

Historical rows are not given invented dates. A one-time fill copies a date
only from that week's own snapshot, and only when the raw value still matches.
Placeholder fetch timestamps are left blank.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from runtime.processing.formula import CORE_METRICS

# Placeholder written by the crime and homelessness fetchers before they
# recorded a real observation. Never treat it as an observation date.
FAKE_FETCH_TIMESTAMPS = {
    "2025-01-01T00:00:00Z",
    "2025-01-01T00:00:00+00:00",
}

UNCHANGED = "unchanged"
REVISION = "revision"
NEW_PERIOD = "new_period"
UNDATED_CHANGE = "undated_change"


def observation_column(metric: str) -> str:
    """Flat CSV / history-row name for one core metric's observation date."""
    return f"{metric}_observation_date"


def weekly_boi_headers(metrics: Sequence[str] = CORE_METRICS) -> List[str]:
    """Column order for ``weekly_bugout_index.csv``.

    Each raw value is followed by its observation date. Normalized scores stay
    at the end, as they did before observation dates existed.
    """
    headers = ["date", "bugout_index"]
    for metric in metrics:
        headers.append(metric)
        headers.append(observation_column(metric))
    headers.extend(f"{metric}_normalized" for metric in metrics)
    return headers


def normalize_observation_date(value: Any) -> Optional[str]:
    """Return ``YYYY-MM-DD`` or ``YYYY``, or None if the value is not a real period.

    Placeholder fetch timestamps are rejected. A full timestamp that is not in
    that placeholder set is reduced to its calendar date.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return None
    if text in FAKE_FETCH_TIMESTAMPS:
        return None
    if len(text) == 4 and text.isdigit():
        return text
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        day = text[:10]
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            return None
        return day
    return None


def observation_date_for(_metric: str, payload: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Observation period for one fetcher payload or snapshot metric entry.

    The metric name is part of the call so the CSV column and the payload
    stay paired. Dating itself comes from the payload. Explicit
    ``observation_date`` wins. Otherwise the date is recovered from
    provenance, then from ``fetched_at`` / ``source_fetched_at`` when that
    field is actually a period (FRED date or survey year).
    """
    payload = payload or {}
    explicit = normalize_observation_date(payload.get("observation_date"))
    if explicit:
        return explicit

    provenance = payload.get("provenance") or {}
    kind = provenance.get("kind")
    if kind == "file":
        found = normalize_observation_date(provenance.get("value_month_end"))
        if found:
            return found
    elif kind == "manual":
        found = normalize_observation_date(provenance.get("reference_date"))
        if found:
            return found
    elif kind == "annual":
        found = normalize_observation_date(provenance.get("year"))
        if found:
            return found

    for key in ("fetched_at", "source_fetched_at"):
        found = normalize_observation_date(payload.get(key))
        if found:
            return found
    return None


def raws_match(left: Any, right: Any) -> bool:
    """True when two raw inputs are the same published number."""
    try:
        a = float(left)
        b = float(right)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def classify_core_change(
    previous_raw: Any,
    current_raw: Any,
    previous_observed: Any,
    current_observed: Any,
) -> str:
    """Tell a same-date revision apart from a new observation period.

    Both observation dates must be present. A value change with a missing
    date is ``undated_change`` and must not be labeled a revision.
    """
    if current_raw in ("", None):
        return UNCHANGED
    if previous_raw in ("", None) or raws_match(previous_raw, current_raw):
        return UNCHANGED
    previous = normalize_observation_date(previous_observed)
    current = normalize_observation_date(current_observed)
    if previous and current:
        if previous == current:
            return REVISION
        return NEW_PERIOD
    return UNDATED_CHANGE


def apply_known_dates(
    rows: Iterable[Mapping[str, Any]],
    snapshots_by_date: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Fill blank observation columns from each publication's own snapshot.

    ``snapshots_by_date`` maps a publication date to that week's ``metrics``
    object. A cell is written only when it is blank, the snapshot raw matches
    the row raw, and ``observation_date_for`` returns a real period. Raw
    values are copied through unchanged. Rows with no snapshot keep blanks.
    """
    headers = weekly_boi_headers()
    filled: List[Dict[str, Any]] = []
    for row in rows:
        out = {header: "" if row.get(header) is None else row.get(header, "") for header in headers}
        metrics = snapshots_by_date.get(str(row.get("date"))) or {}
        for metric in CORE_METRICS:
            column = observation_column(metric)
            if str(out.get(column) or "").strip():
                continue
            entry = metrics.get(metric) or {}
            if not raws_match(out.get(metric), entry.get("raw")):
                continue
            observed = observation_date_for(metric, entry)
            if observed:
                out[column] = observed
        filled.append(out)
    return filled


def blank_observation_dates(rows: Iterable[Mapping[str, Any]]) -> List[dict]:
    """Copy rows and turn blank observation cells into None for JSON."""
    columns = [observation_column(metric) for metric in CORE_METRICS]
    copied: List[dict] = []
    for row in rows:
        item = dict(row)
        for column in columns:
            if column in item and str(item[column]).strip() == "":
                item[column] = None
        copied.append(item)
    return copied


def write_weekly_csv(path: Path, rows: Sequence[Mapping[str, Any]], newline: str = "\r\n") -> None:
    """Rewrite the weekly index CSV with the observation-date schema."""
    headers = weekly_boi_headers()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=headers,
            extrasaction="ignore",
            lineterminator=newline,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                header: "" if row.get(header) is None else row.get(header, "")
                for header in headers
            })


def ensure_csv_schema(path: Path) -> bool:
    """Add observation-date columns if the file still has the old header.

    New cells are blank. This does not look up historical snapshots and does
    not invent dates. Returns True when the file was rewritten.
    """
    if not path.exists():
        return False
    newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
    headers = weekly_boi_headers()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) == headers:
            return False
        rows = list(reader)
    write_weekly_csv(path, rows, newline=newline)
    return True
