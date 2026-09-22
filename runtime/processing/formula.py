# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
v1.0.0 scoring formula.

This module is the only copy of the live publisher math:

* endpoints (``METRIC_RANGES``)
* relative weights (``WEIGHTS``, sum 0.72)
* trust inversion (higher trust → higher stability)
* clamp of each normalized score to 0–100
* aggregation ``Σ(normalized × weight) / Σ weight``
* four risk bands (``interpret``)

``runtime/publish/weekly_run.py`` and the Streamlit simulator import it.
In-range inputs match the published weekly numbers, including the
19 September 2026 index of 57.11.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

# Core metrics — must match the v1.0.0 methodology.
CORE_METRICS = [
    "inflation_rate",
    "incident_rate",           # crime rate (per 100k)
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
]

METRIC_RANGES: Dict[str, tuple] = {
    "inflation_rate": (-10, 15),
    "incident_rate": (500, 8000),
    "unemployment_rate": (0, 25),
    "debt_to_gdp_ratio": (0, 200),
    "homelessness_rate": (0, 0.5),
    "trust_in_government": (0, 80),  # trust is inverted (higher = better)
}

WEIGHTS: Dict[str, float] = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_to_gdp_ratio": 0.12,
    "homelessness_rate": 0.09,
    "trust_in_government": 0.12,
}

# Streamlit pages color a score with these class names.
# Keys are interpret()["band_key"]; thresholds are not repeated here.
STABILITY_CSS_CLASS = {
    "high": "stable",
    "moderate": "moderate",
    "low": "severe",
    "critical": "critical",
}


def normalize(raw: float, lo: float, hi: float, inverse: bool = False) -> float:
    """Normalize to 0-100. Higher = more stable. Clamped, including after inversion."""
    if hi == lo:
        return 0.0
    score = (1 - ((raw - lo) / (hi - lo))) * 100
    if inverse:
        score = 100 - score
    return max(0.0, min(100.0, score))


# Name used by the Streamlit scorers and tests/test_scoring.py.
normalize_metric = normalize


def _inverse(metric: str) -> bool:
    return metric == "trust_in_government"


def score_metric(metric: str, raw: float) -> float:
    """Normalize one core metric with v1.0.0 endpoints, inversion, and clamp."""
    lo, hi = METRIC_RANGES[metric]
    return normalize(float(raw), lo, hi, inverse=_inverse(metric))


def compute_index(metric_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate fetcher payloads the way the weekly publisher does.

    Missing or non-numeric inputs are skipped and the denominator shrinks.
    The stored normalized score is rounded to 2 decimals; the index uses the
    unrounded score, then rounds the quotient to 2 decimals.
    """
    total_weighted = 0.0
    total_weight = 0.0
    per_metric = {}
    for metric in CORE_METRICS:
        payload = metric_results.get(metric, {})
        data = payload.get("data") or {}
        raw = data.get(metric)
        if raw is None or not isinstance(raw, (int, float)):
            per_metric[metric] = {"raw": None, "normalized": None, "weight": WEIGHTS[metric]}
            continue
        lo, hi = METRIC_RANGES[metric]
        norm = normalize(float(raw), lo, hi, inverse=_inverse(metric))
        per_metric[metric] = {
            "raw": float(raw),
            "normalized": round(norm, 2),
            "weight": WEIGHTS[metric],
        }
        total_weighted += norm * WEIGHTS[metric]
        total_weight += WEIGHTS[metric]

    index = round(total_weighted / total_weight, 2) if total_weight else 0.0
    return {"index": index, "metrics": per_metric}


def calculate_category_score(
    metrics: Mapping[str, Any],
    metric_ranges: Optional[Mapping[str, tuple]] = None,
    weights: Optional[Mapping[str, float]] = None,
) -> float:
    """Weighted mean of normalized metrics for the simulator and legacy scorer.

    ``metrics`` maps a name to a raw number, or to a dict whose first value is
    that number. Defaults are the v1.0.0 endpoints and weights. The result is
    not rounded; callers that display two decimals should format it.
    """
    ranges = METRIC_RANGES if metric_ranges is None else metric_ranges
    wts = WEIGHTS if weights is None else weights
    total_score = 0.0
    total_weight = 0.0
    for metric, value in metrics.items():
        if isinstance(value, dict):
            value = list(value.values())[0]
        min_value, max_value = ranges[metric]
        weight = wts[metric]
        total_score += normalize(value, min_value, max_value, inverse=_inverse(metric)) * weight
        total_weight += weight
    return total_score / total_weight if total_weight > 0 else 0


def interpret(index: float) -> Dict[str, str]:
    """Four v1.0.0 risk bands. Thresholds are 70, 55, and 40."""
    if index >= 70:
        return {"band": "High Stability", "risk": "Low Risk", "band_key": "high"}
    if index >= 55:
        return {"band": "Moderate Stability", "risk": "Warning Signs", "band_key": "moderate"}
    if index >= 40:
        return {"band": "Low Stability", "risk": "Heightened Risk", "band_key": "low"}
    return {"band": "Critical Instability", "risk": "Collapse Likely", "band_key": "critical"}


def stability_css_class(index: float) -> str:
    """Streamlit CSS class for a score. Thresholds come from ``interpret``."""
    return STABILITY_CSS_CLASS[interpret(index)["band_key"]]
