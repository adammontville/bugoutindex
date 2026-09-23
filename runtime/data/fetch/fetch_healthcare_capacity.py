# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Parked healthcare-capacity stub. Not a BugOut Index input."""
from __future__ import annotations

from .not_wired import refuse


def fetch():
    """Refuse. Healthcare capacity is parked and has no wired source."""
    refuse(
        "fetch_healthcare_capacity",
        "Healthcare capacity is parked (incubating/parked/healthcare_capacity.md), not an active incubating build.",
    )
