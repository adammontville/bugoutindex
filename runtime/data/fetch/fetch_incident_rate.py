# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import calendar
import os
from collections import Counter

"""
Fetcher for violent crime incident rate.
"""

# Resolve path relative to this file so it works from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))

_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def crime_file_provenance(date_labels, last_updated) -> dict:
    """Dating for the local RTCI file. Does not choose the rate.

    ``value_month`` is the lexicographic maximum of the Date strings, which is
    the month ``DataFrame.max`` selects for the published rate. ``file_through``
    is the latest calendar month actually present in the file. Those differ
    when a later month sorts earlier as text (December before September).
    """
    labels = []
    for raw in date_labels:
        text = str(raw).strip()
        if text and text.lower() not in {"nan", "none"}:
            labels.append(text)
    if not labels:
        return {"kind": "file"}
    value_month = max(labels)
    file_through = max(labels, key=_chrono_key)
    updated = []
    for raw in last_updated:
        text = str(raw).strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            updated.append(text[:10])
    provenance = {
        "kind": "file",
        "value_month": value_month,
        "value_month_end": _month_end(value_month),
        "file_through": file_through,
    }
    if updated:
        provenance["file_updated"] = Counter(updated).most_common(1)[0][0]
    return provenance


def _chrono_key(label: str):
    parts = label.split()
    if len(parts) == 2 and parts[0] in _MONTHS and parts[1].isdigit():
        return (int(parts[1]), _MONTHS[parts[0]])
    return (0, 0)


def _month_end(label: str):
    parts = label.split()
    if len(parts) != 2 or parts[0] not in _MONTHS or not parts[1].isdigit():
        return None
    year = int(parts[1])
    month = _MONTHS[parts[0]]
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last:02d}"


def fetch():
    """
    Fetch the latest violent crime incident rate (Real-Time Crime Index)
    """
    import pandas as pd

    # Load the locally downloaded dataset — check multiple candidate paths.
    candidates = [
        os.path.join(_DATA_DIR, "final_sample.csv"),
        "data/final_sample.csv",
        "runtime/data/final_sample.csv",
    ]
    file_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    df = pd.read_csv(file_path)

    # Same month selection as before: lexicographic max of the Date strings,
    # which is the published 2,723 input (September 2024 in the current file).
    # Do not switch this to the latest calendar month without a reviewed revision.
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date]

    # Compute crime rate per 100,000 people
    df_latest["Total Crime"] = df_latest["Violent Crime_mvs_12mo"] + df_latest["Property Crime_mvs_12mo"]
    df_latest["Crime Rate"] = (df_latest["Total Crime"] / df_latest["FBI.Population.Covered"]) * 100000

    # Aggregate to get national average
    national_crime_rate = df_latest["Crime Rate"].mean()

    provenance = crime_file_provenance(
        df["Date"].tolist(),
        df["Last Updated"].tolist() if "Last Updated" in df.columns else [],
    )
    # No fetch timestamp: the file is local and is not re-downloaded here.
    return {
        "status": "success",
        "fetched_at": None,
        "provenance": provenance,
        "data": {
            "incident_rate": float(round(national_crime_rate, 2))
        }
    }


if __name__ == "__main__":
    # Debugging fetcher output
    result = fetch()
    print(result)