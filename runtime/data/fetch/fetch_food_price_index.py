# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Old food-price stub. The weekly companion is ``fetch_food_shadow``.

This module stays fail-closed. It is not on the weekly path and it must
not return a sample index.
"""
from __future__ import annotations

from .not_wired import refuse


def fetch():
    """Refuse. Callers that still import this name get no payload.

    The wired companion is ``runtime.data.fetch.fetch_food_shadow``
    (FRED ``CPIUFDNS``, 12-month food CPI percent change). It is not an
    input to the score. This stub is not that fetcher.
    """
    refuse(
        "fetch_food_price_index",
        "This name is the old stub. The weekly companion is fetch_food_shadow "
        "(FRED CPIUFDNS, 12-month food CPI percent change). "
        "This module is not on the weekly path and is not in the score.",
    )
