import csv
import os
from datetime import datetime

def log_bugout_index(bugout_index, metrics, file_path="data/historical_bugout_index.csv"):
    """Append BugOut Index score to historical CSV file."""
    headers = ["date", "bugout_index"] + list(metrics.keys())

    # Check if the file exists
    file_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)  # Write headers if file is new
        writer.writerow([datetime.today().strftime("%Y-%m-%d"), bugout_index] + list(metrics.values()))

    print(f"Logged BugOut Index: {bugout_index} on {datetime.today().strftime('%Y-%m-%d')}")
