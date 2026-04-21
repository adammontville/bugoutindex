# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import os
import pandas as pd

"""
Fetcher for violent crime incident rate.
"""

# Resolve path relative to this file so it works from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))


def fetch():
    """
    Fetch the latest violent crime incident rate (Real-Time Crime Index)
    """
    # Load the locally downloaded dataset — check multiple candidate paths.
    candidates = [
        os.path.join(_DATA_DIR, "final_sample.csv"),
        "data/final_sample.csv",
        "runtime/data/final_sample.csv",
    ]
    file_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    df = pd.read_csv(file_path)

    # Keep only the most recent month (latest data available)
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date]

    # Compute crime rate per 100,000 people
    df_latest["Total Crime"] = df_latest["Violent Crime_mvs_12mo"] + df_latest["Property Crime_mvs_12mo"]
    df_latest["Crime Rate"] = (df_latest["Total Crime"] / df_latest["FBI.Population.Covered"]) * 100000

    # Aggregate to get national average
    national_crime_rate = df_latest["Crime Rate"].mean()

    return {
        "status": "success",
        "fetched_at": "2025-01-01T00:00:00Z",  # Example fetch timestamp
        "data": {
            "incident_rate": float(round(national_crime_rate, 2))
        }
    }


if __name__ == "__main__":
    # Debugging fetcher output
    result = fetch()
    print(result)