# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Parked air-quality stub. Not a BugOut Index input."""
from __future__ import annotations

from .not_wired import refuse


def fetch():
    """Refuse. Air quality is parked and has no wired source."""
    refuse(
        "fetch_air_quality_index",
        "Air quality is parked (incubating/parked/air_quality_index.md), not an active incubating build.",
    )
