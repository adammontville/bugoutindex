# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Scoring package. The v1.0.0 formula lives in ``formula``."""
from .formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    calculate_category_score,
    compute_index,
    interpret,
    normalize,
    normalize_metric,
    score_metric,
    stability_css_class,
)

__all__ = [
    "CORE_METRICS",
    "METRIC_RANGES",
    "WEIGHTS",
    "calculate_category_score",
    "compute_index",
    "interpret",
    "normalize",
    "normalize_metric",
    "score_metric",
    "stability_css_class",
]
