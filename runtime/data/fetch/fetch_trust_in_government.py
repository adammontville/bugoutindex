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
Trust in government from the annual checklist.

The live input is the ``trust_in_government`` row in
``runtime/data/annual_inputs.csv``. ``runtime/data/edelman-trust-barometer-us.csv``
is a historical archive. A new year column in that file does not change
the score. See ``runtime/data/ANNUAL_INPUTS.md``.
"""

from .annual_inputs import AnnualInputError, load_annual_row


def fetch():
    """Return the checklist trust score, or fail with no invented date."""
    try:
        row = load_annual_row("trust_in_government")
    except AnnualInputError as exc:
        return _failure(str(exc))

    return {
        "status": "success",
        # Survey year only. Do not turn this into YYYY-MM-DD.
        "fetched_at": row["observation_date"],
        "observation_date": row["observation_date"],
        "provenance": {
            "kind": "annual",
            "year": row["observation_date"],
            "observation_period": row["observation_period"],
            "source": row["source"],
            "source_url": row["source_url"],
            "reviewed_at": row["reviewed_at"],
        },
        "data": {"trust_in_government": round(row["value"], 2)},
    }


def _failure(message: str) -> dict:
    return {
        "status": "error",
        "message": message,
        "fetched_at": None,
        "data": {},
    }
