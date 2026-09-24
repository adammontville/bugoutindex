# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Food-price stub. Next companion candidate; the real fetcher is not built."""
from __future__ import annotations

from .not_wired import refuse


def fetch():
    """Refuse until a follow-up implements a real food companion.

    Food prices are the next companion candidate (not a core input). This
    module is intentionally not a FRED or BLS client yet, and it must not
    return a sample index.
    """
    refuse(
        "fetch_food_price_index",
        "Food prices are the next companion candidate, not a wired series. "
        "A real fetcher is a follow-up (incubating/food_price_index.md) and is not in the score.",
    )
