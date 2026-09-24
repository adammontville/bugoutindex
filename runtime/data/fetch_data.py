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

# Parked or not-yet-sourced stubs are intentionally absent. Calling them raises
# NotWiredError (see runtime/data/fetch/not_wired.py). Do not re-add:
#   air_quality_index, healthcare_capacity, natural_disaster_frequency (parked),
#   grid_outages (incubating; no source chosen),
#   food_price_index (next companion candidate; real fetcher is a follow-up).
# This legacy cache is not the weekly publisher.
FETCH_INTERVALS = {
    "inflation_rate": 30,
    "crime_rate": 90,
    "unemployment_rate": 30,
    "debt_to_gdp_ratio": 90,
    "homelessness_rate": 90,
    "trust_in_government": 365,
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
                if result.get("status") == "success":
                    metadata[metric] = result["fetched_at"]
            except ModuleNotFoundError:
                print(f"Fetch logic for {metric} not implemented.")
            except Exception as exc:
                # A NOT_WIRED stub must not abort the other metrics and must
                # not be stored as a successful fetch. Other failures still abort.
                if exc.__class__.__name__ != "NotWiredError":
                    raise
                print(f"{metric} is NOT_WIRED and was not cached: {exc}")

    save_metadata(metadata)

if __name__ == "__main__":
    main()
