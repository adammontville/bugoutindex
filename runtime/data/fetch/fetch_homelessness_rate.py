# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com

"""
Homelessness rate from the annual checklist.

The value, the HUD reference date, and the review date are cells in
``runtime/data/annual_inputs.csv``. There is no HUD API call. See
``runtime/data/ANNUAL_INPUTS.md``.
"""

from .annual_inputs import AnnualInputError, load_annual_row


def fetch():
    """Return the checklist homelessness rate, or fail with no invented date."""
    try:
        row = load_annual_row("homelessness_rate")
    except AnnualInputError as exc:
        return _failure(str(exc))

    return {
        "status": "success",
        # Empty on purpose. The HUD reference date is observation_date.
        # reviewed_at is the date a person wrote, not a fetch clock.
        "fetched_at": None,
        "observation_date": row["observation_date"],
        "provenance": {
            "kind": "manual",
            "last_set": row["source"],
            "observation_period": row["observation_period"],
            "reference_date": row["observation_date"],
            "source_url": row["source_url"],
            "reviewed_at": row["reviewed_at"],
        },
        "data": {"homelessness_rate": row["value"]},
    }


def _failure(message: str) -> dict:
    return {
        "status": "error",
        "message": message,
        "fetched_at": None,
        "data": {},
    }
