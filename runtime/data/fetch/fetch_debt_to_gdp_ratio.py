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
#     """Fetch the latest Debt-to-GDP Ratio data."""
#     print("Fetching Debt-to-GDP Ratio...")
#     # Simulate fetching data
#     return {"status": "success", "fetched_at": "2025-01-01T00:00:00Z", "data": {"ratio": 120.5}}
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# Constants
FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = st.secrets["FRED_API_KEY"]
SERIES_ID = "GFDEGDQ188S"  # Federal Debt as Percent of GDP

def fetch():
    """Fetch the latest debt-to-GDP ratio from the FRED API."""
    if not FRED_API_KEY:
        raise EnvironmentError("FRED_API_KEY is not set in the environment variables.")

    # Define query parameters
    params = {
        "series_id": SERIES_ID,
        "api_key": FRED_API_KEY,
        "file_type": "json",  # Request JSON format
        "sort_order": "desc",  # Get the latest data first
        "limit": 1  # Fetch only the latest observation
    }

    try:
        response = requests.get(FRED_API_BASE_URL, params=params)
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        data = response.json()

        # Debugging: Print response for verification
        print("DEBUG: API Response:", data)

        # Extract the latest observation
        latest_observation = data["observations"][0]
        debt_to_gdp_ratio = float(latest_observation["value"])
        observation_date = latest_observation["date"]

        # Return the fetched data
        return {
            "status": "success",
            "fetched_at": observation_date,
            "data": {"debt_to_gdp_ratio": debt_to_gdp_ratio}
        }
    except requests.RequestException as e:
        return {"status": "error", "message": f"Request error: {str(e)}"}
    except KeyError as e:
        return {"status": "error", "message": f"Missing data in API response: {e}"}