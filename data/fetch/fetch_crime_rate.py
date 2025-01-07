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
#     """Fetch the latest crime rate data."""
#     print("Fetching crime rate...")
#     # Simulate fetching data
#     return {"status": "success", "fetched_at": "2025-01-01T00:00:00Z", "data": {"rate": 450.0}}
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# Constants
FBI_API_BASE_URL = "https://api.usa.gov/crime/fbi/cde/LATEST/estimates/national"
FBI_API_KEY = os.getenv("FBI_API_KEY").strip()

def fetch():
    """Fetch the latest national crime data from the FBI API."""
    if not FBI_API_KEY:
        raise EnvironmentError("FBI_API_KEY is not set in the environment variables.")

    # Define query parameters
    params = {
        "api_key": FBI_API_KEY,
        "page": 1,  # Optional, for pagination if needed
        "per_page": 1  # Fetch only the latest data
    }

    try:
        # Make the API request
        response = requests.get(FBI_API_BASE_URL, params=params)
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        data = response.json()

        # Extract the latest crime data
        latest_data = data.get("results", [{}])[0]
        if not latest_data:
            raise ValueError("No data available in the API response.")

        # Extract relevant fields
        violent_crime = latest_data.get("violent_crime", 0)
        property_crime = latest_data.get("property_crime", 0)
        year = latest_data.get("year", "Unknown")

        # Return the fetched data
        return {
            "status": "success",
            "fetched_at": year,
            "data": {
                "violent_crime": violent_crime,
                "property_crime": property_crime
            }
        }
    except requests.RequestException as e:
        print(str(e))
        return {"status": "error", "message": f"Request error: {str(e)}"}
    except KeyError as e:
        return {"status": "error", "message": f"Missing data in API response: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"Data error: {e}"}