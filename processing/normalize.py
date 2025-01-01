"""
BugOutIndex
Copyright (C) 2025 Your Name or Organization

This program is dual-licensed under the AGPL-3.0 and a commercial license.

You may use, modify, and distribute this software under the terms of the
GNU Affero General Public License v3.0 as published by the Free Software Foundation.

For proprietary or commercial use, please contact: your-email@example.com
"""
def normalize_metric(raw_value, min_value, max_value):
    """Normalize a raw value to a 0-100 scale."""
    if max_value == min_value:
        return 0  # Avoid division by zero
    return (1 - ((raw_value - min_value) / (max_value - min_value))) * 100

