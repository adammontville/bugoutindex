# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Gallup confidence in institutions, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. Edelman Trust Barometer US Government stays the scored trust
input (``trust_in_government`` in ``runtime/data/annual_inputs.csv``).

Each stored figure is "a great deal" plus "quite a lot" of confidence.
The checklist holds the current annual reading only: Congress, the
presidency, the U.S. Supreme Court, and the average of the 14 institutions
Gallup has measured each year since 1993, when that average is in the
cited article. This module does not request Gallup's site and does not
keep a historical archive.

Cadence is annual, typically a June poll. A person replaces the rows in
``runtime/data/gallup_confidence_shadow.csv`` when Gallup publishes the
next update. See ``runtime/data/TRUST_SHADOWS.md``.
"""
from __future__ import annotations

from pathlib import Path

from runtime.data.fetch.manual_checklist import ChecklistError, build_payload, load_series
from runtime.util.redact import redact_secrets

_HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = _HERE.parent / "gallup_confidence_shadow.csv"
SOURCE_URL = "https://news.gallup.com/poll/1597/confidence-institutions.aspx"
# Current year only. One row per series. Do not grow this into Gallup's archive.
SERIES = {
    "gallup_congress": "Congress",
    "gallup_presidency": "The presidency",
    "gallup_supreme_court": "The U.S. Supreme Court",
    "gallup_core_institutions": "14 institutions measured each year since 1993",
}
MAX_ROWS = 1
_EXTRA = {
    "reading": "percent with a great deal or quite a lot of confidence",
    "cadence": "annual",
    "source_url": SOURCE_URL,
    "checklist": "runtime/data/gallup_confidence_shadow.csv",
    "average_definition": (
        "Average of the 14 institutions Gallup has measured each year since 1993: "
        "the presidency, Congress, the public schools, the Supreme Court, the military, "
        "the criminal justice system, the police, banks, big business, organized labor, "
        "the medical system, newspapers, television news, and the church or organized religion"
    ),
    "levels_note": (
        "Not interchangeable with the Edelman Trust Barometer US Government "
        "figure used in the BugOut Index score"
    ),
    "license_note": (
        "Current annual reading only, entered by hand from the cited Gallup article. "
        "This checklist is not a republication of Gallup's historical series. "
        "Continuous republication of Gallup data may require permission."
    ),
}


def fetch(path: Path | None = None) -> dict:
    """Return the current annual rows, or fail with no invented date."""
    table = Path(path) if path is not None else DEFAULT_TABLE
    try:
        points = load_series(
            table,
            required=SERIES,
            max_rows_per_series=MAX_ROWS,
            label="Gallup confidence",
        )
    except ChecklistError as exc:
        return build_payload(SERIES, {}, [redact_secrets(str(exc))], extra=_EXTRA)
    except Exception as exc:  # noqa: BLE001
        return build_payload(
            SERIES,
            {},
            [redact_secrets(f"Gallup confidence: {exc}")],
            extra=_EXTRA,
        )
    return build_payload(SERIES, points, [], extra=_EXTRA)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
