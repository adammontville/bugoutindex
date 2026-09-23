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
Module Description:
<Add a description of this module here>
"""


# Manual annual input from the 2024 HUD Annual Homeless Assessment Report,
# Part 1 (January point-in-time count). There is no HUD API call. Do not
# invent a fetch timestamp. See runtime/static/markdown/homeless_rate.md.
HOMELESSNESS_RATE = 0.23
PROVENANCE = {
    "kind": "manual",
    "last_set": "2024 HUD AHAR",
    "observation_period": "January 2024 point-in-time count",
    "reference_date": "2024-01-01",
}


def fetch():
    """Return the manually maintained homelessness rate."""
    return {
        "status": "success",
        "fetched_at": None,
        "observation_date": PROVENANCE["reference_date"],
        "provenance": dict(PROVENANCE),
        "data": {"homelessness_rate": HOMELESSNESS_RATE},
    }
