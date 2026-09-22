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
Manages the top-level score calculation.
"""
import importlib
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# This module is sometimes executed as a script with cwd = runtime/.
_RUNTIME_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RUNTIME_DIR.parent
for _path in (str(_REPO_ROOT), str(_RUNTIME_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from runtime.processing.formula import (  # noqa: E402
    CORE_METRICS as metric_names,
    calculate_category_score,
)


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

# Fetch the data dynamically
metrics = {}
for metric in metric_names:
    try:
        module = importlib.import_module(f"data.fetch.fetch_{metric}")
        fetched_data = module.fetch()
        test = fetched_data["data"].get(metric.split("_")[0], 0)
        metrics[metric] = fetched_data["data"]
    except ModuleNotFoundError:
        print(f"EXCEPTION: fetch module for {metric} not implemented.")
    except Exception as e:
        print(f"Error fetching {metric}: {str(e)}")


# Calculate overall score with the shared v1.0.0 formula.
overall_score = calculate_category_score(metrics)
log_bugout_index(overall_score, metrics)
