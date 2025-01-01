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
from processing.normalize import normalize_metric

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
        total_score += normalize_metric(value, min_value, max_value) * weight
        total_weight += weight
    return total_score / total_weight if total_weight > 0 else 0

