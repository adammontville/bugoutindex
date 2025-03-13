# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import pandas as pd

"""
Fetcher for violent crime incident rate.
"""
def fetch():
    """
    Fetch the latest violent crime incident rate (Real-Time Crime Index)
    """
    # Load the locally downloaded dataset
    file_path = "data/final_sample.csv"  # Adjust the path as needed
    df = pd.read_csv(file_path)

    # Keep only the most recent month (latest data available)
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date]

    # Compute crime rate per 100,000 people
    df_latest["Total Crime"] = df_latest["Violent Crime_mvs_12mo"] + df_latest["Property Crime_mvs_12mo"]
    df_latest["Crime Rate"] = (df_latest["Total Crime"] / df_latest["FBI.Population.Covered"]) * 100000

    # Aggregate to get national average
    national_crime_rate = df_latest["Crime Rate"].mean()

    print(f"National Crime Rate: {national_crime_rate:.2f} per 100,000 people")

    return {
        "status": "success",
        "fetched_at": "2025-01-01T00:00:00Z",  # Example fetch timestamp
        "data": {
            "incident_rate": round(national_crime_rate, 2)  # Rounded to two decimal places
        }
    }


if __name__ == "__main__":
    # Debugging fetcher output
    result = fetch()
    print(result)