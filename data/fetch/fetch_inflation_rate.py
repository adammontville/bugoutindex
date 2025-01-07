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
# def fetch():
#     """Fetch the latest inflation rate data."""
#     print("Fetching inflation rate...")
#     # Simulate fetching data
#     return {"status": "success", "fetched_at": "2025-01-01T00:00:00Z", "data": {"rate": 2.5}}
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.getenv("FRED_API_KEY").strip()
SERIES_ID = "CPIAUCSL"

def fetch():
    """Fetch the year-over-year inflation rate from the FRED API."""
    if not FRED_API_KEY:
        raise EnvironmentError("FRED_API_KEY is not set in the environment variables.")

    params_current = {
        "series_id": SERIES_ID,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1  # Fetch latest CPI value
    }

    try:
        # Fetch current CPI value
        response_current = requests.get(FRED_API_BASE_URL, params=params_current)
        response_current.raise_for_status()
        data_current = response_current.json()
        current_cpi = float(data_current["observations"][0]["value"])
        current_date = data_current["observations"][0]["date"]

        # Fetch CPI value from 1 year ago
        params_previous = params_current.copy()
        params_previous["observation_start"] = str(int(current_date[:4]) - 1) + current_date[4:]
        params_previous["observation_end"] = params_previous["observation_start"]
        response_previous = requests.get(FRED_API_BASE_URL, params=params_previous)
        response_previous.raise_for_status()
        data_previous = response_previous.json()
        previous_cpi = float(data_previous["observations"][0]["value"])

        # Calculate the inflation rate
        inflation_rate = ((current_cpi - previous_cpi) / previous_cpi) * 100

        return {
            "status": "success",
            "fetched_at": current_date,
            "data": {"rate": inflation_rate}
        }

    except requests.RequestException as e:
        return {"status": "error", "message": f"Request error: {str(e)}"}
    except (KeyError, IndexError) as e:
        return {"status": "error", "message": f"Data parsing error: {e}"}
