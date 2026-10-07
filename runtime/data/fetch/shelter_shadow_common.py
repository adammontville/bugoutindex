# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Shared shape for local shelter companions.

These series are not inputs. ``compute_index`` never reads them. HUD AHAR
stays the annual national homelessness anchor. Each companion names its
own geography. A city or county figure is not a U.S. figure.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional


def valid_day(value: object) -> Optional[str]:
    """Calendar day as ``YYYY-MM-DD``, or None.

    A Socrata timestamp is reduced to the date. A value that is not a
    calendar day is dropped. This does not stamp the clock.
    """
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 10:
        return None
    day = text[:10]
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return None
    return day


def whole_count(value: object) -> Optional[int]:
    """Whole-person count, or None if the cell is not one."""
    if value in ("", None, "."):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        return None
    if number != number.to_integral_value() or number < 0:
        return None
    return int(number)


def assemble(
    series: Dict[str, str],
    parsed: Dict[str, list],
    errors: List[str],
    *,
    geography: str,
    scope: str,
    dataset_id: str,
    source_url: str,
    reading: str,
    message: str = "",
    extra: Optional[dict] = None,
) -> dict:
    """Public payload. ``in_bugout_index`` is always false."""
    values: Dict[str, object] = {}
    dates: Dict[str, str] = {}
    observations: Dict[str, list] = {}
    for name in series:
        rows = list(parsed.get(name) or [])
        observations[name] = rows
        if rows:
            values[name] = rows[-1]["value"]
            dates[name] = rows[-1]["date"]
        else:
            values[name] = None
    filled = [name for name, value in values.items() if value is not None]
    if len(filled) == len(series) and not errors:
        status = "success"
    elif filled:
        status = "partial"
    else:
        status = "error"
    payload: Dict[str, object] = {
        "status": status,
        "in_bugout_index": False,
        "geography": geography,
        "scope": scope,
        "dataset_id": dataset_id,
        "source_url": source_url,
        "series_ids": {name: series[name] for name in series},
        "reading": reading,
        "values": values,
        "dates": dates,
        "observations": observations,
        "errors": list(errors),
    }
    if extra:
        payload.update(extra)
    if message:
        payload["message"] = message
    elif status == "error" and errors:
        payload["message"] = "; ".join(errors)
    return payload
