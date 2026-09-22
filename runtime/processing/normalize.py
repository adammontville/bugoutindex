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
Normalization entry point.

The implementation, including the 0–100 clamp, is ``formula.normalize``.
"""
from .formula import normalize as normalize_metric

__all__ = ["normalize_metric"]
