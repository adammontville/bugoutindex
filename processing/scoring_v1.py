"""
BugOutIndex
Copyright (C) 2025 Your Name or Organization

This program is dual-licensed under the AGPL-3.0 and a commercial license.

You may use, modify, and distribute this software under the terms of the
GNU Affero General Public License v3.0 as published by the Free Software Foundation.

For proprietary or commercial use, please contact: your-email@example.com
"""
from processing.normalize import normalize_metric

def calculate_category_score(metrics, weights):
    """Calculate the weighted score for a category."""
    return sum(normalize_metric(metrics[m], *weights[m]) * weights[m][2] for m in metrics)

