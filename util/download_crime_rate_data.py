import os
import requests
import pandas as pd
from datetime import datetime

# RTCI GitHub raw file URL
GITHUB_FILE_URL = "https://github.com/AH-Datalytics/rtci/blob/development/data/final_sample.csv"
LOCAL_FILE_PATH = "../data/final_sample.csv"
GITHUB_API_URL = "https://api.github.com/repos/AH-Datalytics/rtci/commits?path=data/final_sample.csv"

def get_github_latest_commit_date():
    """Fetch the latest commit date for the dataset from GitHub."""
    try:
        response = requests.get(GITHUB_API_URL, headers={"Accept": "application/vnd.github.v3+json"})
        response.raise_for_status()
        latest_commit = response.json()[0]
        commit_date = latest_commit["commit"]["committer"]["date"]
        return datetime.strptime(commit_date, "%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"Error fetching commit date: {e}")
        return None

def get_local_file_modified_date():
    """Get the last modified date of the local dataset file."""
    if not os.path.exists(LOCAL_FILE_PATH):
        return None
    modified_timestamp = os.path.getmtime(LOCAL_FILE_PATH)
    return datetime.fromtimestamp(modified_timestamp)

def download_latest_data():
    """Download the latest RTCI crime data and overwrite the local file."""
    try:
        response = requests.get(GITHUB_FILE_URL, stream=True)
        response.raise_for_status()
        with open(LOCAL_FILE_PATH, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print("✅ RTCI dataset updated successfully.")
    except Exception as e:
        print(f"Error downloading the latest dataset: {e}")

def check_and_update_crime_data():
    """Check if the RTCI dataset has been updated and download if necessary."""
    github_date = get_github_latest_commit_date()
    local_date = get_local_file_modified_date()

    if github_date and (not local_date or github_date > local_date):
        print(f"📢 New dataset available! Updating from {local_date} to {github_date}.")
        download_latest_data()
    else:
        print(f"✅ No update needed. Local file is up-to-date (Last modified: {local_date}).")

if __name__ == "__main__":
    check_and_update_crime_data()