# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Pew public trust in government, shown beside the BugOut Index.

This series is not an input. ``compute_index`` never reads it, and it has
no weight. Edelman Trust Barometer US Government stays the scored trust
input (``trust_in_government`` in ``runtime/data/annual_inputs.csv``).

The stored figure is the share who say they trust the government in
Washington to do what is right just about always or most of the time.
Pew's published combined share on the chart is the value. This module
does not add the "just about always" and "most of the time" columns
itself, and it does not download Pew's full series.

Cadence is irregular. A person updates
``runtime/data/pew_trust_shadow.csv`` when Pew publishes a new wave.
See ``runtime/data/TRUST_SHADOWS.md``.
"""
from __future__ import annotations

from pathlib import Path

from runtime.data.fetch.manual_checklist import ChecklistError, build_payload, load_series
from runtime.util.redact import redact_secrets

_HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = _HERE.parent / "pew_trust_shadow.csv"
SOURCE_URL = (
    "https://www.pewresearch.org/politics/2025/12/04/public-trust-in-government-1958-2025/"
)
# One series. A short excerpt of recent waves is allowed. The full
# 1958–2025 archive is not.
SERIES = {
    "pew_public_trust": "just about always or most of the time",
}
MAX_ROWS = 12
_EXTRA = {
    "reading": (
        "share who trust the government in Washington to do what is right "
        "just about always or most of the time"
    ),
    "cadence": "irregular",
    "source_url": SOURCE_URL,
    "checklist": "runtime/data/pew_trust_shadow.csv",
    "levels_note": (
        "Not interchangeable with the Edelman Trust Barometer US Government "
        "figure used in the BugOut Index score"
    ),
    "license_note": (
        "Short excerpt of recent Pew waves, stored with attribution. "
        "The weekly job does not download or republish the full series."
    ),
}


def fetch(path: Path | None = None) -> dict:
    """Return the checklist waves, or fail with no invented date."""
    table = Path(path) if path is not None else DEFAULT_TABLE
    try:
        points = load_series(
            table,
            required=SERIES,
            max_rows_per_series=MAX_ROWS,
            label="Pew public trust",
        )
    except ChecklistError as exc:
        return build_payload(SERIES, {}, [redact_secrets(str(exc))], extra=_EXTRA)
    except Exception as exc:  # noqa: BLE001
        return build_payload(
            SERIES,
            {},
            [redact_secrets(f"Pew public trust: {exc}")],
            extra=_EXTRA,
        )
    return build_payload(SERIES, points, [], extra=_EXTRA)


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), indent=2))
