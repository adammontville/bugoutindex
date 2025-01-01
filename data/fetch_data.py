"""
BugOutIndex
Copyright (C) 2025 Your Name or Organization

This program is dual-licensed under the AGPL-3.0 and a commercial license.

You may use, modify, and distribute this software under the terms of the
GNU Affero General Public License v3.0 as published by the Free Software Foundation.

For proprietary or commercial use, please contact: your-email@example.com
"""
import json
from datetime import datetime, timedelta
import os

# Define fetch intervals in days
FETCH_INTERVALS = {
    "inflation_rate": 30,
    "crime_rate": 90,
    "air_quality_index": 7
}

# Path to the metadata file
METADATA_FILE = "data/cache/last_fetched.json"

def load_metadata():
    """Load last fetched metadata from file."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save metadata to file."""
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=4)

def needs_fetch(metric, last_fetched):
    """Determine if a metric needs to be fetched."""
    interval = FETCH_INTERVALS.get(metric, 30)  # Default to 30 days if not specified
    if not last_fetched:
        return True  # Fetch if no record exists
    last_date = datetime.fromisoformat(last_fetched)
    return datetime.utcnow() > last_date + timedelta(days=interval)

def fetch_data(metric):
    """Simulate data fetching for a specific metric."""
    print(f"Fetching data for {metric}...")
    # Placeholder: Replace with actual data fetching logic
    # For example, fetching from an API or downloading a file
    return {"status": "success", "fetched_at": datetime.utcnow().isoformat()}

def main():
    """Main function to manage data fetching."""
    # Load last fetched metadata
    metadata = load_metadata()

    # Iterate through each metric and check if fetching is needed
    for metric in FETCH_INTERVALS.keys():
        last_fetched = metadata.get(metric)
        if needs_fetch(metric, last_fetched):
            result = fetch_data(metric)
            if result["status"] == "success":
                # Update the last fetched time
                metadata[metric] = result["fetched_at"]

    # Save updated metadata
    save_metadata(metadata)

if __name__ == "__main__":
    main()
