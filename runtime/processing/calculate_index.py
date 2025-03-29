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
from runtime.processing.log_history import log_bugout_index
from runtime.processing.scoring_v1 import calculate_category_score

# Define the metrics to fetch
metric_names = [
    "inflation_rate",
    "incident_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
]

# Fetch the data dynamically
metrics = {}
for metric in metric_names:
    try:
        module = importlib.import_module(f"runtime.data.fetch.fetch_{metric}")
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
