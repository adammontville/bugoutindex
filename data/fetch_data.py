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
import importlib
import json
from datetime import datetime, timedelta
import os

FETCH_INTERVALS = {
    "inflation_rate": 30,
    "crime_rate": 90,
    "air_quality_index": 7,
    "unemployment_rate": 30,
    "debt_to_gdp_ratio": 90,
    "homelessness_rate": 90,
    "trust_in_government": 365,
    "grid_outages": 30,
    "food_price_index": 30,
    "healthcare_capacity": 30,
    "natural_disaster_frequency": 30
}

METADATA_FILE = "data/cache/last_fetched.json"

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=4)

def needs_fetch(metric, last_fetched):
    interval = FETCH_INTERVALS.get(metric, 30)
    if not last_fetched:
        return True
    last_date = datetime.fromisoformat(last_fetched)
    return datetime.utcnow() > last_date + timedelta(days=interval)

def main():
    metadata = load_metadata()

    for metric in FETCH_INTERVALS.keys():
        last_fetched = metadata.get(metric)
        if needs_fetch(metric, last_fetched):
            try:
                module = importlib.import_module(f"fetch.fetch_{metric}")
                result = module.fetch()
                if result["status"] == "success":
                    metadata[metric] = result["fetched_at"]
            except ModuleNotFoundError:
                print(f"Fetch logic for {metric} not implemented.")

    save_metadata(metadata)

if __name__ == "__main__":
    main()
