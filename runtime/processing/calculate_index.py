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
from datetime import datetime

# Define the metrics to fetch
metric_names = [
    "inflation_rate",
    "incident_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
]

def normalize_metric(raw_value, min_value, max_value, inverse=False):
    """Normalize a raw value to a 0-100 scale. Inverts if needed."""
    if max_value == min_value:
        return 0  # Avoid division by zero
    norm_score = (1 - ((raw_value - min_value) / (max_value - min_value))) * 100
    return 100 - norm_score if inverse else norm_score  # Invert for stability metrics

def calculate_category_score(metrics, metric_ranges, weights):
    """Calculate the weighted score for a category."""
    total_score = 0
    total_weight = 0
    for metric, value in metrics.items():
        # Extract the numeric value for scoring
        if isinstance(value, dict):
            value = list(value.values())[0]  # Extract the first numeric value
        min_value, max_value = metric_ranges[metric]
        weight = weights[metric]

        # Invert normalization for trust_in_government (higher trust = higher BOI)
        inverse = metric == "trust_in_government"

        total_score += normalize_metric(value, min_value, max_value, inverse) * weight
        total_weight += weight
    return total_score / total_weight if total_weight > 0 else 0


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


# Ranges for normalization
metric_ranges = {
    "inflation_rate": (-10, 15),
    "incident_rate": (500, 8000),
    "unemployment_rate": (0, 25),
    "debt_to_gdp_ratio": (0, 200),
    "homelessness_rate": (0, 0.5),
    "trust_in_government": (0, 80),
}

# Define weights for BOI calculation
weights = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_to_gdp_ratio": 0.12,
    "homelessness_rate": 0.09,
    "trust_in_government": 0.12,
}

# Calculate overall score
overall_score = calculate_category_score(metrics, metric_ranges, weights)
log_bugout_index(overall_score, metrics)
