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
from processing.log_history import log_bugout_index
from processing.scoring_v1 import calculate_category_score

# Define the metrics to fetch
metric_names = [
    "inflation_rate",
    "crime_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
]

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
    "inflation_rate": (0, 10),  # Example range
    "crime_rate": (1000, 4000),  # Example range
    "unemployment_rate": (0, 20),  # Example range
    "debt_to_gdp_ratio": (0, 200),  # Example range
    "homelessness_rate": (0, 1),  # Example range (percent of population)
    "trust_in_government": (0, 100),
}

# Weights for scoring
weights = {
    "inflation_rate": 0.15,
    "crime_rate": 0.12,
    "unemployment_rate": 0.1,
    "debt_to_gdp_ratio": 0.07,
    "homelessness_rate": 0.09,
    "trust_in_government": 0.09,
}

# Calculate overall score
overall_score = calculate_category_score(metrics, metric_ranges, weights)
log_bugout_index(overall_score, metrics)
