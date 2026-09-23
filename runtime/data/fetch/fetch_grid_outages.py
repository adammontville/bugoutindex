# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Grid-outages stub. Still incubating; no source has been chosen."""
from __future__ import annotations

from .not_wired import refuse


def fetch():
    """Refuse until a real public source is chosen and reviewed.

    The exploration brief is ``incubating/grid_outages.md``. This module is
    not on the weekly path and must not return a sample hour count.
    """
    refuse(
        "fetch_grid_outages",
        "Grid outages remain incubating until a real source is chosen "
        "(incubating/grid_outages.md). No series is approved, and none is wired into the weekly job.",
    )
