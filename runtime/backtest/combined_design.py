# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Research replay of one combined methodology-2.0 design.

This module does not publish a score. It does not change
``runtime.processing.formula``, the weekly job, ``docs/data/latest.json``,
or the weekly history.

The design, and the variants around it:

* Inflation and unemployment use frozen 1970–2006 p2–p98 endpoints.
* Debt-to-GDP is a change, not a level. The recommended change is the
  four-quarter percentage-point difference. The one-quarter change is
  the variant.
* One financial-stress input. The recommended series is the VIX monthly
  mean, with endpoints frozen on 1990–2006 (the series starts in 1990).
  The Chicago Fed NFCI credit subindex is the variant.
* Two weight sets move some of the homelessness and trust weight onto
  that financial input. Crime keeps the 1.1.1 weight and the 500–8,000
  endpoints.
* Bands are the live 70/55/40 cutoffs, plus one episode alternative
  anchored inside the reference window.

The out-of-sample decision window is January 2007 through August 2026.
January 1990 through December 2006 is reported and labeled in-sample.
"""
from __future__ import annotations

import argparse
import csv
import json
from calendar import month_abbr, monthrange
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Mapping, Optional, Sequence

from runtime.backtest.harness import (
    PUBLISHED_DATE,
    cpi_yoy,
    format_float,
    iter_months,
    load_published_raws,
    prior_year_date,
    score_published_inputs,
)
from runtime.data.fetch.annual_inputs import load_annual_row
from runtime.processing.formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    compute_index,
    interpret,
    normalize,
)

REFERENCE_START = "1970-01-01"
REFERENCE_END = "2006-12-01"
DEBT_REFERENCE_END = "2006-10-01"
VIX_REFERENCE_START = "1990-01-01"
VIX_REFERENCE_END = "2006-12-01"
# NBER recession of July 1990–March 1991. The episode anchor is the VIX
# peak inside this window, not a cutoff fit on 2008 or 2020.
RECESSION_START = "1990-07-01"
RECESSION_END = "1991-03-01"
CALM_START = "1995-01-01"
CALM_END = "2006-12-01"
HISTORY_START = "1990-01-01"
REPLAY_START = "2007-01-01"
REPLAY_END = "2026-08-01"
CALM_REPLAY_START = "2015-01-01"
CALM_REPLAY_END = "2019-12-01"
CRIME_START = "2018-01-01"
GAP_MONTH = "2025-10-01"
TODAY_VIX_WEEK = "2026-10-09"

PACKAGE_DIR = Path(__file__).resolve().parent
CALIBRATION_DIR = PACKAGE_DIR / "fixtures" / "calibration"
V2_FIXTURE_DIR = PACKAGE_DIR / "fixtures" / "v2"
OUTPUT_DIR = PACKAGE_DIR / "output"
NOTE_NAME = "COMBINED_DESIGN.md"
MONTHLY_NAME = "combined_design_monthly.csv"
SUMMARY_NAME = "combined_design_summary.csv"
WEEKLY_NAME = "combined_design_weekly.csv"
CHART_NAME = "combined_design_chart.svg"
ROOT = PACKAGE_DIR.parents[1]
LATEST_PATH = ROOT / "docs" / "data" / "latest.json"

# Half of the 0.21 homelessness-plus-trust block moves to financial stress.
W1 = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_change": 0.12,
    "homelessness_rate": 0.045,
    "trust_in_government": 0.06,
    "financial_stress": 0.105,
}
# A smaller move: 0.03 from homelessness and 0.03 from trust.
W2 = {
    "inflation_rate": 0.15,
    "incident_rate": 0.12,
    "unemployment_rate": 0.12,
    "debt_change": 0.12,
    "homelessness_rate": 0.06,
    "trust_in_government": 0.09,
    "financial_stress": 0.06,
}

KEY_DATES = (
    ("2008-10-01", "Oct 2008"),
    ("2009-10-01", "Oct 2009"),
    ("2020-03-01", "Mar 2020"),
    ("2020-04-01", "Apr 2020"),
    ("2022-06-01", "Jun 2022"),
)

SUMMARY_WINDOWS = (
    ("in_sample", "1990–2006, in-sample", HISTORY_START, REFERENCE_END),
    ("out_of_sample", "Jan 2007–Aug 2026", REPLAY_START, REPLAY_END),
    ("2008", "Dec 2007–Dec 2009", "2007-12-01", "2009-12-01"),
    ("2020", "2020", "2020-01-01", "2020-12-01"),
    ("2022", "2022", "2022-01-01", "2022-12-01"),
    ("2015_2019", "2015–2019", CALM_REPLAY_START, CALM_REPLAY_END),
)

_BANDS = (
    "High Stability",
    "Moderate Stability",
    "Low Stability",
    "Critical Instability",
)
_SHORT_BAND = {
    "High Stability": "High",
    "Moderate Stability": "Moderate",
    "Low Stability": "Low",
    "Critical Instability": "Critical",
}
_NORM_FIELDS = (
    ("inflation_rate", "w2_norm_inflation"),
    ("unemployment_rate", "w2_norm_unemployment"),
    ("debt_change", "w2_norm_debt"),
    ("incident_rate", "w2_norm_crime"),
    ("homelessness_rate", "w2_norm_homelessness"),
    ("trust_in_government", "w2_norm_trust"),
    ("financial_stress", "w2_norm_financial"),
)


def percentile(values: Sequence[float], p: float) -> float:
    """Linear percentile, NumPy type 7, with ``p`` on a 0–100 scale."""
    xs = sorted(float(value) for value in values)
    if not xs:
        raise ValueError("percentile of an empty sample")
    if len(xs) == 1:
        return xs[0]
    rank = (p / 100.0) * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _load_series(path: Path, value_col: Optional[str] = None) -> dict[str, float]:
    points: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if len(fields) < 2:
            raise ValueError(f"{path} needs a date column and a value column")
        column = value_col or fields[1]
        for row in reader:
            day = (row.get(fields[0]) or "").strip()
            raw = (row.get(column) or "").strip()
            if day and raw:
                points[day] = float(raw)
    if not points:
        raise ValueError(f"{path} has no observations")
    return points


def load_bundle() -> dict:
    """Offline fixtures. No network and no FRED key."""
    crime = {}
    with (V2_FIXTURE_DIR / "RTCI_monthly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            crime[row["observation_date"]] = float(row["incident_rate_population_weighted"])
    return {
        "reference_cpi": _load_series(CALIBRATION_DIR / "CPIAUCSL.csv"),
        "reference_unemployment": _load_series(CALIBRATION_DIR / "UNRATE.csv"),
        "reference_debt": _load_series(CALIBRATION_DIR / "GFDEGDQ188S.csv"),
        "replay_cpi": _load_series(V2_FIXTURE_DIR / "CPIAUCSL.csv"),
        "replay_unemployment": _load_series(V2_FIXTURE_DIR / "LNS14000000.csv"),
        "replay_debt": _load_series(CALIBRATION_DIR / "GFDEGDQ188S_replay.csv"),
        "vix_reference": _load_series(CALIBRATION_DIR / "VIXCLS_monthly.csv"),
        "vix_replay": _load_series(V2_FIXTURE_DIR / "VIXCLS_monthly.csv", "vix_month_mean"),
        "vix_weekly": _load_series(V2_FIXTURE_DIR / "VIXCLS_weekly.csv", "vix_week_mean"),
        "nfci_weekly": _load_series(V2_FIXTURE_DIR / "NFCICREDIT_weekly.csv", "credit"),
        "crime": crime,
    }


def checklist_pins() -> dict[str, float]:
    homelessness = load_annual_row("homelessness_rate")
    trust = load_annual_row("trust_in_government")
    return {
        "homelessness_rate": float(homelessness["value"]),
        "trust_in_government": float(trust["value"]),
        "homelessness_observation_date": str(homelessness["observation_date"]),
        "trust_observation_date": str(trust["observation_date"]),
    }


def _yoy(levels: Mapping[str, float], day: str) -> Optional[float]:
    previous = prior_year_date(day)
    if day not in levels or previous not in levels or levels[previous] == 0:
        return None
    return cpi_yoy(levels[day], levels[previous])


def _asof(series: Mapping[str, float], day: str) -> tuple[Optional[float], str]:
    available = [stamp for stamp in series if stamp <= day]
    if not available:
        return None, ""
    stamp = max(available)
    return series[stamp], stamp


def _shift_quarter(day: str, quarters: int) -> str:
    year = int(day[:4])
    month = int(day[5:7]) - 3 * quarters
    while month <= 0:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}-01"


def _crime_for(crime: Mapping[str, float], day: str) -> tuple[Optional[float], str]:
    if day < CRIME_START:
        return None, "excluded"
    if day in crime:
        return crime[day], "observed"
    last = max(crime)
    if day > last:
        return crime[last], "carried_forward"
    return None, "excluded"


def _between(day: str, start: str, end: str) -> bool:
    return start <= day <= end


def debt_levels(bundle: Mapping) -> dict[str, float]:
    """Quarterly debt-to-GDP. The reference file wins through October 2006."""
    series = dict(bundle["reference_debt"])
    for day, value in bundle["replay_debt"].items():
        if day > DEBT_REFERENCE_END:
            series[day] = value
    return series


def debt_change_sample(series: Mapping[str, float], quarters: int, start: str, end: str) -> list[tuple[str, float]]:
    """Quarter-start changes only. Carried months are not extra observations."""
    points = []
    for day in sorted(series):
        if not _between(day, start, end):
            continue
        previous = _shift_quarter(day, quarters)
        if previous in series:
            points.append((day, series[day] - series[previous]))
    if not points:
        raise ValueError(f"no debt-change observations for {quarters} quarters")
    return points


def _change_asof(series: Mapping[str, float], day: str, quarters: int) -> tuple[Optional[float], str]:
    level, stamp = _asof(series, day)
    if level is None:
        return None, ""
    previous = _shift_quarter(stamp, quarters)
    if previous not in series:
        return None, stamp
    return series[stamp] - series[previous], stamp


def _monthly_mean(weekly: Mapping[str, float]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for day, value in weekly.items():
        buckets.setdefault(day[:7] + "-01", []).append(value)
    return {month: sum(values) / len(values) for month, values in buckets.items()}


def _pair(points: Sequence[tuple[str, float]]) -> dict:
    values = [value for _, value in points]
    return {
        "lo": percentile(values, 2),
        "hi": percentile(values, 98),
        "p50": percentile(values, 50),
        "n": len(values),
        "min": min(values),
        "max": max(values),
    }


def fit_endpoints(bundle: Mapping) -> dict:
    """Frozen endpoints. Nothing here is fit on a month after December 2006."""
    inflation = []
    for day in iter_months(REFERENCE_START, REFERENCE_END):
        value = _yoy(bundle["reference_cpi"], day)
        if value is not None:
            inflation.append((day, value))
    unemployment = [
        (day, bundle["reference_unemployment"][day])
        for day in iter_months(REFERENCE_START, REFERENCE_END)
        if day in bundle["reference_unemployment"]
    ]
    levels = debt_levels(bundle)
    level_points = [
        (day, levels[day])
        for day in sorted(levels)
        if _between(day, REFERENCE_START, DEBT_REFERENCE_END)
    ]
    yoy = debt_change_sample(levels, 4, "1971-01-01", DEBT_REFERENCE_END)
    qoq = debt_change_sample(levels, 1, "1970-04-01", DEBT_REFERENCE_END)
    vix = [
        (day, value)
        for day, value in bundle["vix_reference"].items()
        if _between(day, VIX_REFERENCE_START, VIX_REFERENCE_END)
    ]
    nfci = _monthly_mean(bundle["nfci_weekly"])
    nfci_points = [
        (day, value)
        for day, value in nfci.items()
        if _between(day, "1971-01-01", REFERENCE_END)
    ]
    return {
        "inflation": _pair(inflation),
        "unemployment": _pair(unemployment),
        "debt_level": _pair(level_points),
        "debt_yoy": _pair(yoy),
        "debt_qoq": _pair(qoq),
        "vix": _pair(vix),
        "nfci": _pair(nfci_points),
        "nfci_monthly": nfci,
    }


def _ranges(ends: Mapping, debt_key: str, financial_key: str) -> dict[str, tuple[float, float]]:
    return {
        "inflation_rate": (ends["inflation"]["lo"], ends["inflation"]["hi"]),
        "unemployment_rate": (ends["unemployment"]["lo"], ends["unemployment"]["hi"]),
        "incident_rate": METRIC_RANGES["incident_rate"],
        "debt_change": (ends[debt_key]["lo"], ends[debt_key]["hi"]),
        "homelessness_rate": METRIC_RANGES["homelessness_rate"],
        "trust_in_government": METRIC_RANGES["trust_in_government"],
        "financial_stress": (ends[financial_key]["lo"], ends[financial_key]["hi"]),
    }


def _score(raws: Mapping[str, Optional[float]], ranges: Mapping[str, tuple], weights: Mapping[str, float]) -> dict:
    """Weighted mean of normalized inputs. Missing inputs shrink the denominator.

    The index uses the unrounded component, then rounds to two decimals.
    Higher is more stable. Trust is the only inverted input.
    """
    total = 0.0
    weight_sum = 0.0
    norms = {}
    for metric, weight in weights.items():
        raw = raws.get(metric)
        if raw is None or not isinstance(raw, (int, float)):
            norms[metric] = None
            continue
        lo, hi = ranges[metric]
        value = normalize(float(raw), lo, hi, inverse=metric == "trust_in_government")
        norms[metric] = value
        total += value * weight
        weight_sum += weight
    index = round(total / weight_sum, 2) if weight_sum else None
    return {"index": index, "norms": norms, "denominator": weight_sum}


def _v1_score(raws: Mapping[str, Optional[float]]) -> dict:
    payload = {
        metric: {"data": {metric: raws[metric]}}
        for metric in CORE_METRICS
        if isinstance(raws.get(metric), (int, float))
    }
    if not payload:
        return {"index": None, "band": None, "denominator": 0.0}
    index = compute_index(payload)["index"]
    return {
        "index": index,
        "band": interpret(index)["band"],
        "denominator": sum(WEIGHTS[metric] for metric in payload),
    }


def episode_band(index: float, stress: float, calm: float) -> str:
    """Four bands from two reference-window anchors.

    Critical is below the stress anchor. High is at or above the calm
    median. The midpoint splits Low and Moderate.
    """
    midpoint = (stress + calm) / 2.0
    if index >= calm:
        return "High Stability"
    if index >= midpoint:
        return "Moderate Stability"
    if index >= stress:
        return "Low Stability"
    return "Critical Instability"


def _window_name(day: str) -> str:
    if day <= REFERENCE_END:
        return "in_sample"
    if _between(day, "2007-12-01", "2009-12-01"):
        return "2008"
    if _between(day, "2020-01-01", "2020-12-01"):
        return "2020"
    if _between(day, "2022-01-01", "2022-12-01"):
        return "2022"
    if _between(day, CALM_REPLAY_START, CALM_REPLAY_END):
        return "2015_2019"
    return "history"


def _month_inputs(day: str, bundle: Mapping, pins: Mapping, levels: Mapping, nfci: Mapping) -> dict:
    if day <= REFERENCE_END:
        inflation = _yoy(bundle["reference_cpi"], day)
        unemployment = bundle["reference_unemployment"].get(day)
        vix = bundle["vix_reference"].get(day)
    else:
        inflation = _yoy(bundle["replay_cpi"], day)
        unemployment = bundle["replay_unemployment"].get(day)
        vix = bundle["vix_replay"].get(day)
    debt_level, debt_date = _asof(levels, day)
    debt_yoy, _yoy_date = _change_asof(levels, day, 4)
    debt_qoq, _qoq_date = _change_asof(levels, day, 1)
    crime, crime_status = _crime_for(bundle["crime"], day)
    return {
        "inflation_rate": inflation,
        "unemployment_rate": unemployment,
        "debt_level": debt_level,
        "debt_observation_date": debt_date,
        "debt_yoy": debt_yoy,
        "debt_qoq": debt_qoq,
        "incident_rate": crime,
        "incident_status": crime_status,
        "homelessness_rate": float(pins["homelessness_rate"]),
        "trust_in_government": float(pins["trust_in_government"]),
        "vix": vix,
        "nfci": nfci.get(day),
    }


def _research_raws(inputs: Mapping, debt_key: str, financial_key: str) -> dict[str, Optional[float]]:
    return {
        "inflation_rate": inputs["inflation_rate"],
        "incident_rate": inputs["incident_rate"],
        "unemployment_rate": inputs["unemployment_rate"],
        "debt_change": inputs[debt_key],
        "homelessness_rate": inputs["homelessness_rate"],
        "trust_in_government": inputs["trust_in_government"],
        "financial_stress": inputs[financial_key],
    }


def _v1_raws(inputs: Mapping) -> dict[str, Optional[float]]:
    return {
        "inflation_rate": inputs["inflation_rate"],
        "incident_rate": inputs["incident_rate"],
        "unemployment_rate": inputs["unemployment_rate"],
        "debt_to_gdp_ratio": inputs["debt_level"],
        "homelessness_rate": inputs["homelessness_rate"],
        "trust_in_government": inputs["trust_in_government"],
    }


def _apply_scores(inputs: Mapping, ends: Mapping) -> dict:
    ranges_vix_yoy = _ranges(ends, "debt_yoy", "vix")
    ranges_vix_qoq = _ranges(ends, "debt_qoq", "vix")
    ranges_nfci_yoy = _ranges(ends, "debt_yoy", "nfci")
    v1 = _v1_score(_v1_raws(inputs))
    w1 = _score(_research_raws(inputs, "debt_yoy", "vix"), ranges_vix_yoy, W1)
    w2 = _score(_research_raws(inputs, "debt_yoy", "vix"), ranges_vix_yoy, W2)
    qoq = _score(_research_raws(inputs, "debt_qoq", "vix"), ranges_vix_qoq, W2)
    nfci = _score(_research_raws(inputs, "debt_yoy", "nfci"), ranges_nfci_yoy, W2)
    return {
        "v1_index": v1["index"],
        "v1_band": v1["band"],
        "v1_denominator": v1["denominator"],
        "w1_index": w1["index"],
        "w1_band": None if w1["index"] is None else interpret(w1["index"])["band"],
        "w2_index": w2["index"],
        "w2_band": None if w2["index"] is None else interpret(w2["index"])["band"],
        "w2_denominator": w2["denominator"],
        "w2_norms": w2["norms"],
        "w2_qoq_index": qoq["index"],
        "w2_qoq_band": None if qoq["index"] is None else interpret(qoq["index"])["band"],
        "w2_nfci_index": nfci["index"],
        "w2_nfci_band": None if nfci["index"] is None else interpret(nfci["index"])["band"],
        "w2_nfci_norms": nfci["norms"],
    }


def build_rows(bundle: Optional[Mapping] = None) -> tuple[list[dict], dict]:
    """One row per month from January 1990 through August 2026."""
    bundle = load_bundle() if bundle is None else bundle
    pins = checklist_pins()
    ends = fit_endpoints(bundle)
    levels = debt_levels(bundle)
    rows = []
    for day in iter_months(HISTORY_START, REPLAY_END):
        inputs = _month_inputs(day, bundle, pins, levels, ends["nfci_monthly"])
        scored = _apply_scores(inputs, ends)
        row = {
            "date": day,
            "sample": "in_sample" if day <= REFERENCE_END else "out_of_sample",
            "window": _window_name(day),
            "thin_month": inputs["inflation_rate"] is None or inputs["unemployment_rate"] is None,
            **inputs,
            **scored,
        }
        rows.append(row)
    anchors = _episode_anchors(rows)
    for row in rows:
        if row["w2_index"] is None:
            row["w2_episode_band"] = None
        else:
            row["w2_episode_band"] = episode_band(row["w2_index"], anchors["stress"], anchors["calm"])
    context = {"ends": ends, "anchors": anchors, "pins": pins, "levels": levels, "bundle": bundle}
    return rows, context


def _episode_anchors(rows: Sequence[Mapping]) -> dict:
    """Stress is the VIX peak inside the 1990–91 recession. Calm is the later median.

    Both are taken from months through December 2006. The 2007–2026 path
    does not move them.
    """
    recession = [
        row
        for row in rows
        if _between(str(row["date"]), RECESSION_START, RECESSION_END) and row["vix"] is not None
    ]
    if not recession:
        raise ValueError("1990–91 recession window has no VIX")
    stress_row = sorted(recession, key=lambda row: (-float(row["vix"]), str(row["date"])))[0]
    calm_values = [
        float(row["w2_index"])
        for row in rows
        if _between(str(row["date"]), CALM_START, CALM_END) and row["w2_index"] is not None
    ]
    if not calm_values or stress_row["w2_index"] is None:
        raise ValueError("episode anchors are missing")
    stress = round(float(stress_row["w2_index"]), 2)
    calm = round(percentile(calm_values, 50), 2)
    return {
        "stress_month": str(stress_row["date"]),
        "stress_vix": float(stress_row["vix"]),
        "stress": stress,
        "stress_denominator": float(stress_row["w2_denominator"]),
        "calm": calm,
        "midpoint": round((stress + calm) / 2.0, 2),
    }


def current_reading(bundle: Optional[Mapping] = None, context: Optional[Mapping] = None) -> dict:
    """Score the latest.json raws on the research config without writing the file.

    Unemployment for this row is the September 2026 print in ``latest.json``.
    The monthly BLS fixture ends in August. The VIX is the week ending
    9 October 2026, not the August monthly mean.
    """
    bundle = load_bundle() if bundle is None else bundle
    if context is None:
        _rows, context = build_rows(bundle)
    latest = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    pins = context["pins"]
    published = {metric: float(latest["metrics"][metric]["raw"]) for metric in CORE_METRICS}
    published_score = _v1_score(published)
    restated = dict(published)
    restated["homelessness_rate"] = float(pins["homelessness_rate"])
    restated["trust_in_government"] = float(pins["trust_in_government"])
    restated_score = _v1_score(restated)
    levels = context["levels"]
    publication = str(latest["publication_date"])
    debt_yoy, debt_date = _change_asof(levels, publication, 4)
    debt_qoq, _qoq_date = _change_asof(levels, publication, 1)
    if TODAY_VIX_WEEK not in bundle["vix_weekly"]:
        raise ValueError(f"weekly VIX fixture has no {TODAY_VIX_WEEK}")
    nfci_weeks = [day for day in bundle["nfci_weekly"] if day <= publication]
    nfci_week = max(nfci_weeks)
    inputs = {
        "inflation_rate": published["inflation_rate"],
        "unemployment_rate": published["unemployment_rate"],
        "debt_level": published["debt_to_gdp_ratio"],
        "debt_observation_date": debt_date,
        "debt_yoy": debt_yoy,
        "debt_qoq": debt_qoq,
        "incident_rate": published["incident_rate"],
        "incident_status": "carried_forward",
        "homelessness_rate": float(pins["homelessness_rate"]),
        "trust_in_government": float(pins["trust_in_government"]),
        "vix": bundle["vix_weekly"][TODAY_VIX_WEEK],
        "nfci": bundle["nfci_weekly"][nfci_week],
    }
    scored = _apply_scores(inputs, context["ends"])
    anchors = context["anchors"]
    episode = episode_band(scored["w2_index"], anchors["stress"], anchors["calm"])
    return {
        "date": publication,
        "published_methodology": latest["methodology_version"],
        "published_file_index": latest["bugout_index"],
        "published_index": published_score["index"],
        "published_band": published_score["band"],
        "v1_index": restated_score["index"],
        "v1_band": restated_score["band"],
        "inflation_rate": inputs["inflation_rate"],
        "inflation_date": latest["metrics"]["inflation_rate"]["observation_date"],
        "unemployment_rate": inputs["unemployment_rate"],
        "unemployment_date": latest["metrics"]["unemployment_rate"]["observation_date"],
        "debt_level": inputs["debt_level"],
        "debt_observation_date": debt_date,
        "debt_yoy": debt_yoy,
        "debt_qoq": debt_qoq,
        "incident_rate": inputs["incident_rate"],
        "homelessness_rate": inputs["homelessness_rate"],
        "trust_in_government": inputs["trust_in_government"],
        "vix": inputs["vix"],
        "vix_week": TODAY_VIX_WEEK,
        "nfci": inputs["nfci"],
        "nfci_week": nfci_week,
        "w1_index": scored["w1_index"],
        "w1_band": scored["w1_band"],
        "w2_index": scored["w2_index"],
        "w2_band": scored["w2_band"],
        "w2_denominator": scored["w2_denominator"],
        "w2_norms": scored["w2_norms"],
        "w2_qoq_index": scored["w2_qoq_index"],
        "w2_qoq_band": scored["w2_qoq_band"],
        "w2_nfci_index": scored["w2_nfci_index"],
        "w2_nfci_band": scored["w2_nfci_band"],
        "w2_episode_band": episode,
        "thin_month": False,
    }


def debt_level_ceiling(pins: Mapping[str, float]) -> float:
    """Highest 1.1.1 index once the debt level is stuck at its unstable clamp.

    Inflation, unemployment, and crime are set to the stable end of their
    live scales. Homelessness and trust stay on the checklist. The debt
    slot contributes nothing. This is why a frozen level endpoint cannot
    reach High after the ratio leaves the 1970–2006 range.
    """
    homelessness = normalize(float(pins["homelessness_rate"]), 0, 0.5)
    trust = normalize(float(pins["trust_in_government"]), 0, 80, inverse=True)
    total = 100.0 * (0.15 + 0.12 + 0.12) + homelessness * 0.09 + trust * 0.12
    return round(total / 0.72, 2)


def _band_counts(bands: Sequence[Optional[str]]) -> dict[str, int]:
    counts = {band: 0 for band in _BANDS}
    for band in bands:
        if band in counts:
            counts[band] += 1
    return counts


def summarize(rows: Sequence[Mapping]) -> list[dict]:
    scenarios = (
        ("v1", "v1_index", "v1_band", "1.1.1"),
        ("w1", "w1_index", "w1_band", "W1, four-quarter debt, VIX, live bands"),
        ("w2", "w2_index", "w2_band", "W2, four-quarter debt, VIX, live bands"),
        ("w2_qoq", "w2_qoq_index", "w2_qoq_band", "W2, one-quarter debt, VIX, live bands"),
        ("w2_nfci", "w2_nfci_index", "w2_nfci_band", "W2, four-quarter debt, NFCI, live bands"),
        ("w2_episode", "w2_index", "w2_episode_band", "W2, four-quarter debt, VIX, episode bands"),
    )
    summary = []
    for window_name, title, start, end in SUMMARY_WINDOWS:
        subset = [row for row in rows if start <= str(row["date"]) <= end]
        for scenario, index_key, band_key, label in scenarios:
            indexes = [(float(row[index_key]), str(row["date"])) for row in subset if row[index_key] is not None]
            counts = _band_counts(
                [row[band_key] for row in subset if row[index_key] is not None]
            )
            indexes.sort()
            values = [value for value, _day in indexes]
            summary.append(
                {
                    "scenario": scenario,
                    "scenario_label": label,
                    "window": window_name,
                    "window_title": title,
                    "months": len(indexes),
                    "min_index": None if not indexes else indexes[0][0],
                    "min_date": "" if not indexes else indexes[0][1],
                    "max_index": None if not indexes else indexes[-1][0],
                    "max_date": "" if not indexes else indexes[-1][1],
                    "mean_index": None if not values else mean(values),
                    "stdev_index": None if len(values) < 2 else stdev(values),
                    "high": counts["High Stability"],
                    "moderate": counts["Moderate Stability"],
                    "low": counts["Low Stability"],
                    "critical": counts["Critical Instability"],
                }
            )
    return summary


def _lookup(summary: Sequence[Mapping], scenario: str, window: str) -> Mapping:
    for row in summary:
        if row["scenario"] == scenario and row["window"] == window:
            return row
    raise KeyError((scenario, window))


def _fridays(start: str, end: str) -> list[str]:
    year, month, day = (int(part) for part in start.split("-"))
    cursor = date(year, month, day)
    end_date = date.fromisoformat(end)
    while cursor.weekday() != 4:
        cursor += timedelta(days=1)
    stamps = []
    while cursor <= end_date:
        stamps.append(cursor.isoformat())
        cursor += timedelta(days=7)
    return stamps


def _delta_summary(series: str, sample: str, deltas: list[tuple[str, float]]) -> dict:
    if not deltas:
        return {
            "series": series,
            "sample": sample,
            "weeks": 0,
            "mean_abs_change": None,
            "stdev_change": None,
            "share_flat": None,
            "max_abs_change": None,
            "max_abs_week": "",
            "max_drop": None,
            "max_drop_week": "",
        }
    changes = [change for _, change in deltas]
    max_week, max_abs = max(deltas, key=lambda item: (abs(item[1]), item[0]))
    drop_week, drop = min(deltas, key=lambda item: (item[1], item[0]))
    flat = sum(1 for change in changes if change == 0.0)
    return {
        "series": series,
        "sample": sample,
        "weeks": len(deltas),
        "mean_abs_change": mean(abs(change) for change in changes),
        "stdev_change": stdev(changes) if len(changes) > 1 else 0.0,
        "share_flat": flat / len(changes),
        "max_abs_change": abs(max_abs),
        "max_abs_week": max_week,
        "max_drop": drop,
        "max_drop_week": drop_week,
    }


def weekly_volatility(rows: Sequence[Mapping], bundle: Mapping, ends: Mapping) -> list[dict]:
    """Month-publish steps, and Friday steps that swap in that week's VIX mean.

    CPI, unemployment, the debt change, crime, and the checklist do not
    move inside a month. A monthly-mean VIX does not either, so a Friday
    file of the month score is flat until the month changes. The week-mean
    VIX is the path that can tick between Fridays.
    """
    by_month = {str(row["date"]): row for row in rows if row["sample"] == "out_of_sample"}
    ranges = _ranges(ends, "debt_yoy", "vix")
    last_friday = date(2026, 8, monthrange(2026, 8)[1])
    while last_friday.weekday() != 4:
        last_friday -= timedelta(days=1)
    stamps = [
        stamp
        for stamp in _fridays(REPLAY_START, last_friday.isoformat())
        if stamp[:7] + "-01" in by_month and stamp in bundle["vix_weekly"]
    ]
    month_points = []
    week_points = []
    for stamp in stamps:
        month = stamp[:7] + "-01"
        row = by_month[month]
        month_points.append((stamp, month, row["w2_index"], row["thin_month"]))
        raws = _research_raws(row, "debt_yoy", "vix")
        raws["financial_stress"] = bundle["vix_weekly"][stamp]
        scored = _score(raws, ranges, W2)
        week_points.append((stamp, month, scored["index"], row["thin_month"]))

    def _pairs(points, predicate):
        deltas = []
        for prev, cur in zip(points, points[1:]):
            if prev[2] is None or cur[2] is None or not predicate(prev, cur):
                continue
            deltas.append((cur[0], round(float(cur[2]) - float(prev[2]), 2)))
        return deltas

    output = []
    for name, points in (("w2_month_publish", month_points), ("w2_week_vix", week_points)):
        output.append(_delta_summary(name, "within_month", _pairs(points, lambda prev, cur: prev[1] == cur[1])))
        output.append(_delta_summary(name, "all_fridays", _pairs(points, lambda prev, cur: True)))
        output.append(
            _delta_summary(
                name,
                "gap_excluded",
                _pairs(points, lambda prev, cur: not prev[3] and not cur[3]),
            )
        )
    oos = [row for row in rows if row["sample"] == "out_of_sample"]
    for name, key in (("v1_monthly", "v1_index"), ("w2_monthly", "w2_index")):
        all_steps = []
        kept_steps = []
        for prev, cur in zip(oos, oos[1:]):
            if prev[key] is None or cur[key] is None:
                continue
            change = (str(cur["date"]), round(float(cur[key]) - float(prev[key]), 2))
            all_steps.append(change)
            if not prev["thin_month"] and not cur["thin_month"]:
                kept_steps.append(change)
        output.append(_delta_summary(name, "all_months", all_steps))
        output.append(_delta_summary(name, "gap_excluded", kept_steps))
    return output


def _by_date(rows: Sequence[Mapping]) -> dict[str, Mapping]:
    return {str(row["date"]): row for row in rows}


def _month_label(day: str) -> str:
    year, month, _day = day.split("-")
    return f"{month_abbr[int(month)]} {year}"


def _num(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value):.{digits}f}"


def _cell(index: object, band: object) -> str:
    if index is None or band is None:
        return ""
    return f"{float(index):.2f} {_SHORT_BAND[str(band)]}"


def _endpoint(stats: Mapping) -> str:
    return f"{stats['lo']:.5f} to {stats['hi']:.5f}"


def _crime_span(bundle: Mapping) -> dict:
    values = list(bundle["crime"].values())
    lo, hi = METRIC_RANGES["incident_rate"]
    norms = [normalize(value, lo, hi) for value in values]
    return {
        "n": len(values),
        "raw_min": min(values),
        "raw_max": max(values),
        "norm_min": min(norms),
        "norm_max": max(norms),
        "scale_used": (max(norms) - min(norms)) / 100.0,
    }


def _closest_to_median(rows: Sequence[Mapping], start: str, end: str, key: str) -> Mapping:
    subset = [row for row in rows if _between(str(row["date"]), start, end) and row[key] is not None]
    typical = percentile([float(row[key]) for row in subset], 50)
    return min(subset, key=lambda row: (abs(float(row[key]) - typical), str(row["date"])))


def render_markdown(report: Mapping) -> str:
    rows = report["rows"]
    today = report["today"]
    ends = report["ends"]
    anchors = report["anchors"]
    summary = report["summary"]
    weekly = report["weekly"]
    pins = report["pins"]
    by_date = _by_date(rows)
    calm = _closest_to_median(rows, CALM_REPLAY_START, CALM_REPLAY_END, "w2_index")
    oos = _lookup(summary, "w2", "out_of_sample")
    w1_oos = _lookup(summary, "w1", "out_of_sample")
    qoq_oos = _lookup(summary, "w2_qoq", "out_of_sample")
    nfci_oos = _lookup(summary, "w2_nfci", "out_of_sample")
    episode_oos = _lookup(summary, "w2_episode", "out_of_sample")
    v1_oos = _lookup(summary, "v1", "out_of_sample")
    ins = _lookup(summary, "w2", "in_sample")
    calm_window = _lookup(summary, "w2", "2015_2019")
    crisis_2008 = _lookup(summary, "w2", "2008")
    year_2020 = _lookup(summary, "w2", "2020")
    year_2022 = _lookup(summary, "w2", "2022")
    critical = [row for row in rows if row["sample"] == "out_of_sample" and row["w2_band"] == "Critical Instability"]
    july_2020 = by_date["2020-07-01"]
    ceiling = report["ceiling"]
    crime = report["crime"]
    recommend = report["recommend"]
    lines = [
        "# Combined 2.0 design, research replay",
        "",
        "Research only. This note does not change `compute_index`, methodology 1.1.1, `docs/data/latest.json`, or the weekly history. It does not cut a version.",
        "",
        _recommendation_lead(recommend, today, oos),
        "",
        "The recommended config is weight set W2, the four-quarter change in the debt-to-GDP ratio, the VIX monthly mean, and the live bands at 70, 55, and 40. W1, the one-quarter debt change, NFCI in place of the VIX, and the episode bands were run and are not the recommendation. Crime stays on the 1.1.1 weight and the 500–8,000 endpoints.",
        "",
        "## Comparison",
        "",
        "1.1.1 uses the live endpoints, the debt-to-GDP level, and the live weights. Homelessness is 0.22 and trust is 39 on every historical month, the methodology 1.1.1 checklist, not a reconstructed path. W1 and W2 use the frozen inflation and unemployment endpoints, a debt change, and a financial-stress input. The episode column is the W2 score under the alternative bands, not a different index.",
        "",
        "| Reading | 1.1.1 | W1, YoY, VIX | W2, YoY, VIX | W2, QoQ, VIX | W2, YoY, NFCI | W2 episode |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day, label in KEY_DATES:
        row = by_date[day]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    _cell(row["v1_index"], row["v1_band"]),
                    _cell(row["w1_index"], row["w1_band"]),
                    _cell(row["w2_index"], row["w2_band"]),
                    _cell(row["w2_qoq_index"], row["w2_qoq_band"]),
                    _cell(row["w2_nfci_index"], row["w2_nfci_band"]),
                    _cell(row["w2_index"], row["w2_episode_band"]),
                ]
            )
            + " |"
        )
    lines.append(
        "| "
        + " | ".join(
            [
                f"{_month_label(str(calm['date']))} (2015–19 typical)",
                _cell(calm["v1_index"], calm["v1_band"]),
                _cell(calm["w1_index"], calm["w1_band"]),
                _cell(calm["w2_index"], calm["w2_band"]),
                _cell(calm["w2_qoq_index"], calm["w2_qoq_band"]),
                _cell(calm["w2_nfci_index"], calm["w2_nfci_band"]),
                _cell(calm["w2_index"], calm["w2_episode_band"]),
            ]
        )
        + " |"
    )
    august = by_date[REPLAY_END]
    lines.append(
        "| "
        + " | ".join(
            [
                "Aug 2026 monthly",
                _cell(august["v1_index"], august["v1_band"]),
                _cell(august["w1_index"], august["w1_band"]),
                _cell(august["w2_index"], august["w2_band"]),
                _cell(august["w2_qoq_index"], august["w2_qoq_band"]),
                _cell(august["w2_nfci_index"], august["w2_nfci_band"]),
                _cell(august["w2_index"], august["w2_episode_band"]),
            ]
        )
        + " |"
    )
    lines.append(
        "| "
        + " | ".join(
            [
                f"Today ({today['date']})",
                _cell(today["v1_index"], today["v1_band"]),
                _cell(today["w1_index"], today["w1_band"]),
                _cell(today["w2_index"], today["w2_band"]),
                _cell(today["w2_qoq_index"], today["w2_qoq_band"]),
                _cell(today["w2_nfci_index"], today["w2_nfci_band"]),
                _cell(today["w2_index"], today["w2_episode_band"]),
            ]
        )
        + " |"
    )
    lines.extend(
        [
            "",
            f"Today is not the August row. August unemployment in the monthly fixture is the August print. Today uses the September unemployment rate {today['unemployment_rate']:.1f} from `latest.json` (observation {today['unemployment_date']}) and the VIX week ending {today['vix_week']} at {today['vix']:.3f}. Inflation is still the August year-over-year rate {today['inflation_rate']:.2f}. The debt change is carried from {today['debt_observation_date']}. Crime is the April 2026 Nationwide Full Sample rate {today['incident_rate']:.2f}, carried forward. The 1.1.1 column on Today restates homelessness and trust to the checklist ({pins['homelessness_rate']:.2f} and {pins['trust_in_government']:.0f}) and is {today['v1_index']:.2f}. The file on disk stays methodology {today['published_methodology']} at {today['published_file_index']:.2f}.",
            "",
            f"2015–2019 typical is the out-of-sample month closest to the W2 median of that window. That month is {_month_label(str(calm['date']))} at {float(calm['w2_index']):.2f}. The window itself runs {calm_window['min_index']:.2f} to {calm_window['max_index']:.2f}.",
            "",
            "## Do 2008 and 2020 separate?",
            "",
            _separation_paragraph(by_date, calm_window, crisis_2008, year_2020, year_2022, critical, oos),
            "",
            "March 2020 stays Moderate on W2. The VIX is at its stressed clamp, and its weight is 0.06. Unemployment is still low and the four-quarter debt change has not jumped yet. Both print in April. A financial-stress slot of this size cannot carry March by itself. June 2022 also stays Moderate, and it overlaps the bottom of 2015–2019. Inflation is the stressed input that month. Unemployment is below the frozen p2, so it clamps to fully stable, and the debt ratio is falling, so the change clamps to fully stable as well. The design does not put 2022 in its own crisis band. Methodology 1.1.1 called June 2022 Low because the wide CPI scale and the high debt level both pulled the index down.",
            "",
            _critical_paragraph(critical, by_date),
            "",
            "## Weights",
            "",
            "Homelessness and trust are 0.09 and 0.12 under 1.1.1, together 0.21 of the 0.72 weight sum. Both are one checklist point, so they shift the level of every month and do not mark a crisis. The financial input is paid for by cutting them, not by cutting inflation, unemployment, crime, or the debt slot.",
            "",
            "| Set | Inflation | Crime | Unemployment | Debt change | Homelessness | Trust | Financial | Sum |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| 1.1.1 | 0.15 | 0.12 | 0.12 | 0.12 level | 0.09 | 0.12 | none | 0.72 |",
            "| W1, half the checklist block | 0.15 | 0.12 | 0.12 | 0.12 | 0.045 | 0.06 | 0.105 | 0.72 |",
            "| W2, moderate shift | 0.15 | 0.12 | 0.12 | 0.12 | 0.06 | 0.09 | 0.06 | 0.72 |",
            "",
            "W1 moves half of the 0.21 block. W2 moves 0.06, about 29 percent of it. The debt slot stays 0.12. Only the series in that slot changes, from the level to the change.",
            "",
            _weight_verdict(by_date, today, w1_oos, oos),
            "",
            "## Debt change",
            "",
            _debt_level_paragraph(ends, ceiling, report["debt_stuck"]),
            "",
            f"The recommended replacement is the four-quarter percentage-point change: this quarter's ratio minus the ratio four quarters earlier. On quarter-start dates from January 1971 through October 2006 the change runs {ends['debt_yoy']['min']:.2f} to {ends['debt_yoy']['max']:.2f}. The frozen p2–p98 endpoints are {_endpoint(ends['debt_yoy'])} ({ends['debt_yoy']['n']} quarters). A change above the top endpoint clamps to 0. A change below the bottom endpoint, a falling ratio, clamps to 100. Other months carry the latest quarter, the same way the live publisher carries the level.",
            "",
            f"The variant is the one-quarter change. Its 1970–2006 p2–p98 endpoints are {_endpoint(ends['debt_qoq'])} ({ends['debt_qoq']['n']} quarters). October 2008, October 2009, April 2020, and June 2022 land on the same clamp under both changes, so those four W2 readings match. They come apart inside the COVID shock. In July 2020 the four-quarter change is still {july_2020['debt_yoy']:.2f} percentage points, which is max stress on the frozen scale. The one-quarter change is {july_2020['debt_qoq']:.2f}, below the frozen floor, so the debt slot clamps to fully stable while unemployment is still elevated. The four-quarter change keeps the debt slot stressed through the rest of the shock. The quarterly change marks the debt slot calm in the same quarter. The one-quarter change also scores today {_cell(today['w2_qoq_index'], today['w2_qoq_band'])}, while the four-quarter change scores today {_cell(today['w2_index'], today['w2_band'])}. That is the reason to prefer the four-quarter change.",
            "",
            f"Out of sample, W2 with the one-quarter change runs {qoq_oos['min_index']:.2f}–{qoq_oos['max_index']:.2f} and counts High {qoq_oos['high']}, Moderate {qoq_oos['moderate']}, Low {qoq_oos['low']}, Critical {qoq_oos['critical']}. The four-quarter counts are High {oos['high']}, Moderate {oos['moderate']}, Low {oos['low']}, Critical {oos['critical']}.",
            "",
            "## Financial stress",
            "",
            f"The recommended input is one series: the calendar-month mean of the daily VIX close. The reference window is January 1990 through December 2006, because the CBOE series starts in 1990. It still ends before the 2007 replay, and it is not a rolling window. p2–p98 on that window is {_endpoint(ends['vix'])} ({ends['vix']['n']} months). Higher is less stable. October 2008 and March 2020 both clamp to 0. The public source is the CBOE daily history. The same close is what FRED publishes as VIXCLS. No licensed credit spread is in this replay.",
            "",
            f"The variant is the Chicago Fed NFCI credit subindex, alone, without the VIX. It is a public weekly series. The scored input is the mean of the Fridays in the month. p2–p98 on January 1971 through December 2006 is {_endpoint(ends['nfci'])} ({ends['nfci']['n']} months). It does mark 2008. It does not mark March 2020 as a credit break: the monthly mean that month normalizes to {by_date['2020-03-01']['w2_nfci_norms']['financial_stress']:.1f} on this scale, near the middle, because the Federal Reserve's facilities sat on top of the credit indexes. The W2 NFCI reading for March 2020 is {_cell(by_date['2020-03-01']['w2_nfci_index'], by_date['2020-03-01']['w2_nfci_band'])}. The VIX reading for the same month is {_cell(by_date['2020-03-01']['w2_index'], by_date['2020-03-01']['w2_band'])}. Out of sample, NFCI never reaches Critical (High {nfci_oos['high']}, Moderate {nfci_oos['moderate']}, Low {nfci_oos['low']}, Critical {nfci_oos['critical']}, range {nfci_oos['min_index']:.2f}–{nfci_oos['max_index']:.2f}). A blend of VIX and NFCI would dilute the one month the financial slot is there to see. The VIX is the cleaner single input.",
            "",
            "## Crime endpoints",
            "",
            f"Crime stays at 500–8,000, inverted, weight 0.12. There is no RTCI path before January 2018, so a 1970–2006 percentile is not available. Fitting endpoints on 2018–2026 would use the replay itself. That was not done. On the file that does exist, the Nationwide Full Sample rate runs {crime['raw_min']:.2f} to {crime['raw_max']:.2f}, and the live scale only uses {crime['scale_used'] * 100:.1f} percent of the 0–100 norm (norms {crime['norm_min']:.2f} to {crime['norm_max']:.2f}). Crime still compresses the index. Tightening it would be a separate decision, and it would be look-ahead if the fit used these years.",
            "",
            "## Bands",
            "",
            "The recommended bands are the live cutoffs: High at or above 70, Moderate at or above 55, Low at or above 40, Critical below 40. They were not refit on 2008, 2020, or 2022.",
            "",
            _episode_paragraph(anchors, episode_oos, by_date, today, oos, ins),
            "",
            "## Distribution",
            "",
            "January 1990 through December 2006 is inside the VIX reference window and inside the 1970–2006 window used for CPI, unemployment, and the debt change. It is in-sample. Crime is absent before 2018, so the denominator is 0.60 on W2 until then and 0.72 from January 2018. October 2025 drops inflation and unemployment (the appropriations-lapse blank) and the denominator shrinks again. The decision sample is January 2007 through August 2026.",
            "",
            "| Config | Sample | Months | Min | Max | Mean | SD | High | Moderate | Low | Critical |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for scenario, window in (
        ("v1", "out_of_sample"),
        ("w1", "out_of_sample"),
        ("w2", "out_of_sample"),
        ("w2_qoq", "out_of_sample"),
        ("w2_nfci", "out_of_sample"),
        ("w2_episode", "out_of_sample"),
        ("v1", "in_sample"),
        ("w2", "in_sample"),
        ("w2", "2008"),
        ("w2", "2020"),
        ("w2", "2022"),
        ("w2", "2015_2019"),
        ("v1", "2015_2019"),
    ):
        row = _lookup(summary, scenario, window)
        lines.append(
            "| "
            + " | ".join(
                [
                    row["scenario_label"],
                    row["window_title"],
                    str(row["months"]),
                    f"{row['min_index']:.2f}",
                    f"{row['max_index']:.2f}",
                    f"{row['mean_index']:.2f}",
                    f"{row['stdev_index']:.2f}",
                    str(row["high"]),
                    str(row["moderate"]),
                    str(row["low"]),
                    str(row["critical"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"W2 out of sample is High in {oos['high']} of {oos['months']} months and Critical in {oos['critical']}. The 1.1.1 replay of the same months is High in {v1_oos['high']} and Critical in {v1_oos['critical']}, range {v1_oos['min_index']:.2f}–{v1_oos['max_index']:.2f}. The in-sample W2 path is {ins['min_index']:.2f}–{ins['max_index']:.2f}, High {ins['high']}, Moderate {ins['moderate']}, Low {ins['low']}, Critical {ins['critical']}. Do not read the in-sample band counts as confirmation. The endpoints were fit on that era.",
            "",
            f"W2 in the December 2007–December 2009 window: {crisis_2008['min_index']:.2f}–{crisis_2008['max_index']:.2f}, Low {crisis_2008['low']}, Moderate {crisis_2008['moderate']}, High {crisis_2008['high']}, Critical {crisis_2008['critical']}. In 2020: Low {year_2020['low']}, Moderate {year_2020['moderate']}, High {year_2020['high']}, Critical {year_2020['critical']}. In 2022: Moderate {year_2022['moderate']}, High {year_2022['high']}, Low {year_2022['low']}, Critical {year_2022['critical']}, range {year_2022['min_index']:.2f}–{year_2022['max_index']:.2f}.",
            "",
            "### W2 components at the readings that matter",
            "",
            "Norms are 0–100, higher meaning more stable, before the weight. Homelessness and trust are the checklist on every row (norms "
            f"{by_date['2008-10-01']['w2_norms']['homelessness_rate']:.2f} and {by_date['2008-10-01']['w2_norms']['trust_in_government']:.2f}).",
            "",
            "| Reading | Index | Inflation | Unemployment | Debt change | Crime | VIX | Denominator |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    component_rows = [*KEY_DATES, (str(calm["date"]), _month_label(str(calm["date"])))]
    for day, label in component_rows:
        lines.append("| " + _component_cells(by_date[day], label) + " |")
    lines.append("| " + _component_cells(august, "Aug 2026") + " |")
    lines.append("| " + _today_component_cells(today) + " |")
    for row in critical:
        lines.append("| " + _component_cells(row, _month_label(str(row["date"])) + " Critical") + " |")
    lines.extend(
        [
            "",
            "## Volatility",
            "",
            "Two weekly measures, both on January 2007 through August 2026. The month-publish path copies the month's W2 score onto every Friday. CPI, unemployment, the debt change, crime, and the checklist are flat inside a month, and so is a monthly-mean VIX, so that path does not move between Fridays of the same month. The week-VIX path replaces only the financial slot with that Friday's mean of daily closes. The other inputs stay on the month. October 2025 is blank for CPI and unemployment. Steps that touch it are a hole filling back in, not a weekly shock. The gap-excluded rows drop those steps.",
            "",
            "| Path | Sample | Steps | Mean abs | SD of change | Share flat | Largest abs | Largest drop |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in weekly:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["series"]),
                    str(item["sample"]),
                    str(item["weeks"]),
                    _num(item["mean_abs_change"]),
                    _num(item["stdev_change"]),
                    "" if item["share_flat"] is None else f"{float(item['share_flat']) * 100:.1f}%",
                    _num(item["max_abs_change"]),
                    ""
                    if item["max_drop"] is None
                    else (
                        "none"
                        if float(item["max_abs_change"] or 0) == 0
                        else f"{float(item['max_drop']):.2f} ({item['max_drop_week']})"
                    ),
                ]
            )
            + " |"
        )
    w2_month = _weekly(weekly, "w2_monthly", "gap_excluded")
    w2_week = _weekly(weekly, "w2_week_vix", "gap_excluded")
    w2_within = _weekly(weekly, "w2_month_publish", "within_month")
    lines.extend(
        [
            "",
            f"The largest month-to-month W2 move that does not touch October 2025 is {w2_month['max_drop']:.2f} on {w2_month['max_drop_week']}. That step is into April 2020. The month-publish Friday file is flat inside the month (share flat {float(w2_within['share_flat']) * 100:.1f}%). The week-mean VIX is the publish-relevant jitter: gap-excluded mean absolute Friday move {w2_week['mean_abs_change']:.2f}, standard deviation {w2_week['stdev_change']:.2f}.",
            "",
            "## Cadence and freshness",
            "",
            "As of the 9 October 2026 publication. The dates below are the latest observation used for Today. Nothing here is an ALFRED real-time vintage.",
            "",
            "| Input | Cadence | What is scored | Latest observation used | Source |",
            "| --- | --- | --- | --- | --- |",
            f"| Inflation | Monthly | Year-over-year CPI-U | {today['inflation_date']} ({today['inflation_rate']:.2f}) | BLS `CPIAUCSL`, the FRED headline CPI. Reference file through {REFERENCE_END}. Replay file through {REPLAY_END}. October 2025 omitted. |",
            f"| Unemployment | Monthly | The monthly rate | Today uses {today['unemployment_date']} ({today['unemployment_rate']:.1f}). The monthly replay stops at {REPLAY_END} because that is the last CPI month, and the BLS fixture has no September row. | BLS `LNS14000000`. October 2025 omitted. September 2026 exists only on `latest.json`. |",
            f"| Debt change | Quarterly, carried | Four-quarter percentage-point change | {today['debt_observation_date']}, change {today['debt_yoy']:.2f} | FRED `GFDEGDQ188S`. Reference through {DEBT_REFERENCE_END}. Replay through the latest quarter in the fixture. |",
            "| Crime | Monthly, then carried | RTCI Nationwide Full Sample, population-weighted | April 2026, carried after the file ends | AH-Datalytics RTCI. No month before January 2018. |",
            f"| Homelessness | Annual checklist | The level, held on every historical month | {pins['homelessness_observation_date']}, value {pins['homelessness_rate']:.2f} | 2025 HUD AHAR, methodology 1.1.1 checklist. Not a historical path. |",
            f"| Trust | Annual checklist | The level, inverted, held on every historical month | {pins['trust_observation_date']}, value {pins['trust_in_government']:.0f} | 2026 Edelman Trust Barometer, US government. Not a historical path. |",
            f"| VIX | Daily close | Calendar-month mean in the replay. Week mean on the Friday path and on Today. | Month means through {REPLAY_END}. Today uses the week ending {today['vix_week']} ({today['vix']:.3f}). | CBOE daily history. Reference months {VIX_REFERENCE_START} through {VIX_REFERENCE_END} set the endpoints. |",
            f"| NFCI credit (not recommended) | Weekly Friday | Monthly mean of Fridays | Latest Friday on or before the publication date is {today['nfci_week']} ({today['nfci']:.3f}) | Chicago Fed NFCI credit subindex, public CSV. Endpoint window January 1971–December 2006. |",
            "",
            "The VIX reference file stops in December 2006 so a later week cannot move the endpoint. The 2006 months match the replay file. NFCI is fully public. It is still the rejected financial variant, for the March 2020 reason above.",
            "",
            "## If this were 2.0.0",
            "",
            "A published version of this config would be methodology 2.0.0, not 1.2.0. The endpoints, the debt series, the weight vector, and a new input all change what a point means. History rows would keep the `methodology_version` that produced them. The first 2.0.0 week would be a labeled break on the chart, not a restatement of the 1.1.1 number. The 1.1.1 restatement of the current raw inputs is "
            f"{today['v1_index']:.2f} {_SHORT_BAND[today['v1_band']]}. The file on disk is methodology {today['published_methodology']} at {today['published_file_index']:.2f}. Those are not the W2 reading of {today['w2_index']:.2f}. `latest.json` would carry 2.0.0 forward only.",
            "",
            "The release note would name the frozen windows and the rule. CPI, unemployment, and the four-quarter debt change use January 1970 through December 2006 (debt changes from January 1971, because the change needs a year of history). The VIX uses January 1990 through December 2006, because the series starts in 1990. Percentiles are type 7: rank `(p/100) × (n − 1)`, then linear interpolation, p2 and p98, frozen. Crime endpoints stay 500–8,000. Homelessness and trust stay checklist levels. This research does not cut that version, does not rewrite history, and does not draw the break.",
            "",
            "![W2 and methodology 1.1.1, January 1990 through August 2026. The vertical line is January 2007, where the replay leaves the fitting window. Not a published series.](output/combined_design_chart.svg)",
            "",
            "## What this replay is not",
            "",
            "It is not a real-time vintage. FRED and BLS figures are the revised prints in the fixtures. It is not a historical homelessness or trust series. Those two are the current checklist on every month, so part of the gap versus 1.1.1 is a level shift. It does not score Pew, Gallup, or the shelter census. It does not start before 1990, because that is when the VIX starts. The 1980 and 1982 stress years are in the inflation and unemployment endpoints and are not in the index path.",
            "",
        ]
    )
    return "\n".join(lines)


def _recommendation_lead(recommend: bool, today: Mapping, oos: Mapping) -> str:
    if recommend:
        return (
            f"Recommendation: adopt W2 with the four-quarter debt change, the VIX, and the live bands, if a 2.0.0 is cut. "
            f"Today on that config is {today['w2_index']:.2f} {_SHORT_BAND[today['w2_band']]}. "
            f"Out of sample it is Critical in {oos['critical']} of {oos['months']} months, and those months are 2010–2011, not October 2008 and not April 2020. "
            "October 2008, October 2009, and April 2020 are Low, and they sit below the 2015–2019 floor. "
            "The design does not do what Option C did. Option C, in the endpoint-and-band replay, put 59 of 236 months in Critical and scored the current reading High. This note does not recompute Option C. It treats that pattern, Critical sprayed across ordinary months and today pushed into High, as the failure to avoid."
        )
    return (
        f"Recommendation: do not adopt this design. Today on W2 is {today['w2_index']:.2f} {_SHORT_BAND[today['w2_band']]}. "
        "The variants do not separate the crisis troughs from 2015–2019 without pushing the current reading into High or spraying Critical the way Option C did."
    )


def _separation_paragraph(by_date, calm_window, crisis_2008, year_2020, year_2022, critical, oos) -> str:
    oct_2008 = by_date["2008-10-01"]
    oct_2009 = by_date["2009-10-01"]
    mar_2020 = by_date["2020-03-01"]
    apr_2020 = by_date["2020-04-01"]
    jun_2022 = by_date["2022-06-01"]
    return (
        f"On W2, October 2008 is {oct_2008['w2_index']:.2f} {_SHORT_BAND[oct_2008['w2_band']]}, "
        f"October 2009 is {oct_2009['w2_index']:.2f} {_SHORT_BAND[oct_2009['w2_band']]}, "
        f"and April 2020 is {apr_2020['w2_index']:.2f} {_SHORT_BAND[apr_2020['w2_band']]}. "
        f"March 2020 is {mar_2020['w2_index']:.2f} {_SHORT_BAND[mar_2020['w2_band']]}. "
        f"June 2022 is {jun_2022['w2_index']:.2f} {_SHORT_BAND[jun_2022['w2_band']]}. "
        f"The 2015–2019 path runs {calm_window['min_index']:.2f} to {calm_window['max_index']:.2f} "
        f"and never enters Low or Critical (High {calm_window['high']}, Moderate {calm_window['moderate']}). "
        f"Those three troughs sit below that floor. The December 2007–December 2009 window still reaches "
        f"{crisis_2008['max_index']:.2f}, so the edges of the window overlap the bottom of the calm range. The troughs do not. "
        f"Inside that window the count is Low {crisis_2008['low']}, Moderate {crisis_2008['moderate']}, "
        f"range {crisis_2008['min_index']:.2f}–{crisis_2008['max_index']:.2f}. "
        f"2020 is Low in {year_2020['low']} months and Moderate in {year_2020['moderate']}. "
        f"2022 stays Moderate ({year_2022['min_index']:.2f}–{year_2022['max_index']:.2f}) and overlaps the calm floor. "
        f"W2 is Critical in {oos['critical']} out-of-sample months. "
        + (
            "Those Critical months are "
            + ", ".join(f"{_month_label(str(row['date']))} ({float(row['w2_index']):.2f})" for row in critical)
            + ". They are not October 2008 and they are not April 2020."
            if critical
            else "It is never Critical out of sample."
        )
    )


def _critical_paragraph(critical: Sequence[Mapping], by_date: Mapping) -> str:
    if not critical:
        return "W2 has no out-of-sample Critical month under the live bands."
    bits = []
    for row in critical:
        norms = row["w2_norms"]
        bits.append(
            f"{_month_label(str(row['date']))} is {float(row['w2_index']):.2f}, "
            f"with unemployment norm {_fmt_norm(norms['unemployment_rate'])}, "
            f"debt-change norm {_fmt_norm(norms['debt_change'])}, "
            f"VIX norm {_fmt_norm(norms['financial_stress'])}, "
            f"and inflation norm {_fmt_norm(norms['inflation_rate'])}"
            + (
                ""
                if norms["incident_rate"] is None
                else f", crime norm {_fmt_norm(norms['incident_rate'])}"
            )
            + f". The denominator is {float(row['w2_denominator']):.2f}"
            + (" because crime has not started." if norms["incident_rate"] is None else ".")
        )
    oct_2008 = by_date["2008-10-01"]["w2_norms"]
    apr_2020 = by_date["2020-04-01"]["w2_norms"]
    return (
        "The Critical months are the long unemployment aftermath, not the two troughs the bands are being asked about. "
        + " ".join(bits)
        + " October 2008 stays Low because unemployment is only partway stressed "
        + f"(norm {_fmt_norm(oct_2008['unemployment_rate'])}) and inflation is still calm "
        + f"(norm {_fmt_norm(oct_2008['inflation_rate'])}). The VIX and the debt change are both at the unstable clamp, "
        + "and crime is not in the denominator yet. April 2020 stays Low because inflation is at the stable clamp "
        + f"(norm {_fmt_norm(apr_2020['inflation_rate'])}) and crime, present by then, is "
        + f"{_fmt_norm(apr_2020['incident_rate'])} on its wide scale. Unemployment, the debt change, and the VIX are at the unstable clamp that month. "
        + "Those two calm slots are what keep April above 40."
    )


def _debt_level_paragraph(ends: Mapping, ceiling: float, stuck: Mapping) -> str:
    if stuck["all_after_first"] and stuck["first"]:
        stuck_sentence = (
            f"From {_month_label(stuck['first'])} through the end of the replay, every month is above that ceiling "
            f"({stuck['stuck']} months), so a level slot would clamp to 0, the unstable end."
        )
    else:
        stuck_sentence = (
            f"{stuck['stuck']} of {stuck['months']} out-of-sample months are above that ceiling."
        )
    return (
        f"Option A's frozen endpoints, fit on 1970–2006, are {_endpoint(ends['inflation'])} for inflation "
        f"and {_endpoint(ends['unemployment'])} for unemployment. The same window's debt-to-GDP level has p2–p98 "
        f"endpoints {_endpoint(ends['debt_level'])} ({ends['debt_level']['n']} quarters). {stuck_sentence} "
        f"With that clamp, the checklist left where it is, and inflation, unemployment, and crime set to the stable "
        f"end of their scales, the 1.1.1 index tops out at {ceiling:.2f}. High is 70. A level endpoint from this "
        "window cannot reach it. That is why the level is replaced."
    )


def _fmt_norm(value: Optional[float]) -> str:
    if value is None:
        return "missing"
    return f"{value:.1f}"


def _weight_verdict(by_date, today, w1_oos, oos) -> str:
    april = by_date["2020-04-01"]
    august = by_date[REPLAY_END]
    return (
        f"W1 is the set that overcorrects. April 2020 is {_cell(april['w1_index'], april['w1_band'])} on W1 and {_cell(april['w2_index'], april['w2_band'])} on W2. "
        f"August 2026 is {_cell(august['w1_index'], august['w1_band'])} on W1 and {_cell(august['w2_index'], august['w2_band'])} on W2. "
        f"Today is {_cell(today['w1_index'], today['w1_band'])} on W1 and {_cell(today['w2_index'], today['w2_band'])} on W2. "
        f"Out of sample, W1 is Critical in {w1_oos['critical']} months and High in {w1_oos['high']}. W2 is Critical in {oos['critical']} and High in {oos['high']}. "
        "W2 keeps today in Moderate. That is the weight set."
    )


def _episode_paragraph(anchors, episode_oos, by_date, today, oos, insample) -> str:
    same_month = anchors["stress_month"] == insample["min_date"]
    coincidence = (
        " That month is also the lowest in-sample W2 score. The rule did not search for the minimum."
        if same_month
        else ""
    )
    return (
        f"The one alternative is an episode rule, fit only through 2006. "
        f"The stress anchor is the W2 score in the month of the highest VIX inside the July 1990–March 1991 recession, which is {_month_label(anchors['stress_month'])} "
        f"(VIX monthly mean {anchors['stress_vix']:.2f}, W2 {anchors['stress']:.2f}, denominator {anchors['stress_denominator']:.2f} because crime is absent).{coincidence} "
        f"The calm anchor is the median W2 score from January 1995 through December 2006, {anchors['calm']:.2f}. "
        f"The midpoint is {anchors['midpoint']:.2f}. Critical is below the stress anchor, Low is below the midpoint, Moderate is below the calm anchor, and High is at or above it. "
        f"Nothing in that rule looks at 2008, 2020, or 2022. "
        f"Out of sample the episode labels are High {episode_oos['high']}, Moderate {episode_oos['moderate']}, Low {episode_oos['low']}, Critical {episode_oos['critical']}. "
        f"October 2008 would be {_SHORT_BAND[by_date['2008-10-01']['w2_episode_band']]}, "
        f"April 2020 {_SHORT_BAND[by_date['2020-04-01']['w2_episode_band']]}, "
        f"June 2022 {_SHORT_BAND[by_date['2022-06-01']['w2_episode_band']]}, "
        f"and today {_SHORT_BAND[today['w2_episode_band']]}. "
        f"The stress anchor is {anchors['stress']:.2f}, between October 2008 ({float(by_date['2008-10-01']['w2_index']):.2f}) and the two lower troughs, October 2009 ({float(by_date['2009-10-01']['w2_index']):.2f}) and April 2020 ({float(by_date['2020-04-01']['w2_index']):.2f}). "
        f"{_episode_trough_sentence(by_date)}"
        f"That is {episode_oos['critical']} Critical months out of sample, against {oos['critical']} under the live bands. "
        "The live cutoffs already put October 2008, October 2009, and April 2020 in Low, keep 2015–2019 above Low, and leave today in Moderate. "
        f"The episode rule uses the same W2 scores and a higher Critical cutoff ({anchors['stress']:.2f} instead of 40). It is reported and not adopted."
    )


def _episode_trough_sentence(by_date: Mapping) -> str:
    october = _SHORT_BAND[by_date["2009-10-01"]["w2_episode_band"]]
    april = _SHORT_BAND[by_date["2020-04-01"]["w2_episode_band"]]
    if october == april:
        return f"Both of those troughs are {october} under the episode rule. "
    return f"October 2009 is {october} and April 2020 is {april} under the episode rule. "


def _component_cells(row: Mapping, label: str) -> str:
    norms = row["w2_norms"]
    return " | ".join(
        [
            label,
            f"{float(row['w2_index']):.2f}",
            _fmt_norm(norms["inflation_rate"]),
            _fmt_norm(norms["unemployment_rate"]),
            _fmt_norm(norms["debt_change"]),
            _fmt_norm(norms["incident_rate"]),
            _fmt_norm(norms["financial_stress"]),
            f"{float(row['w2_denominator']):.2f}",
        ]
    )


def _today_component_cells(today: Mapping) -> str:
    norms = today["w2_norms"]
    return " | ".join(
        [
            "Today",
            f"{float(today['w2_index']):.2f}",
            _fmt_norm(norms["inflation_rate"]),
            _fmt_norm(norms["unemployment_rate"]),
            _fmt_norm(norms["debt_change"]),
            _fmt_norm(norms["incident_rate"]),
            _fmt_norm(norms["financial_stress"]),
            f"{float(today['w2_denominator']):.2f}",
        ]
    )


def _weekly(weekly: Sequence[Mapping], series: str, sample: str) -> Mapping:
    for item in weekly:
        if item["series"] == series and item["sample"] == sample:
            return item
    raise KeyError((series, sample))


def _should_recommend(rows: Sequence[Mapping], today: Mapping) -> bool:
    """True when W2 separates the named troughs from 2015–2019 without calling today High."""
    by_date = _by_date(rows)
    calm = [
        row
        for row in rows
        if _between(str(row["date"]), CALM_REPLAY_START, CALM_REPLAY_END) and row["w2_index"] is not None
    ]
    troughs = ("2008-10-01", "2009-10-01", "2020-04-01")
    calm_floor = min(float(row["w2_index"]) for row in calm)
    separated = all(float(by_date[day]["w2_index"]) < 55 for day in troughs) and calm_floor > 55
    calm_not_low = all(row["w2_band"] in ("High Stability", "Moderate Stability") for row in calm)
    today_not_high = today["w2_band"] != "High Stability"
    april_not_critical = by_date["2020-04-01"]["w2_band"] != "Critical Instability"
    return separated and calm_not_low and today_not_high and april_not_critical


def render_svg(rows: Sequence[Mapping]) -> str:
    width, height = 960, 420
    left, right, top, bottom = 52, 20, 28, 40
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_lo, y_hi = 30.0, 90.0
    n = max(len(rows) - 1, 1)

    def x_at(index: int) -> float:
        return left + plot_w * index / n

    def y_at(value: float) -> float:
        clamped = min(y_hi, max(y_lo, value))
        return top + plot_h * (1 - (clamped - y_lo) / (y_hi - y_lo))

    def segments(key: str) -> list[str]:
        pieces = []
        current: list[str] = []
        for index, row in enumerate(rows):
            if row["thin_month"] or row[key] is None:
                if len(current) > 1:
                    pieces.append(" ".join(current))
                current = []
                continue
            current.append(f"{x_at(index):.1f},{y_at(float(row[key])):.1f}")
        if len(current) > 1:
            pieces.append(" ".join(current))
        return pieces

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>W2 and methodology 1.1.1, January 1990 through August 2026</title>",
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<text x="52" y="18" font-family="Georgia, serif" font-size="14" fill="#1c1915">Research replay. Not the published index.</text>',
    ]
    for level, label in ((70, "70"), (55, "55"), (40, "40")):
        y = y_at(level)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#d9d3c7" stroke-width="1"/>')
        parts.append(f'<text x="8" y="{y + 4:.1f}" font-family="sans-serif" font-size="11" fill="#6b645b">{label}</text>')
    break_at = next(index for index, row in enumerate(rows) if row["date"] == REPLAY_START)
    x_break = x_at(break_at)
    parts.append(
        f'<line x1="{x_break:.1f}" y1="{top}" x2="{x_break:.1f}" y2="{height - bottom}" stroke="#8a8175" stroke-dasharray="3 3"/>'
    )
    parts.append(
        f'<text x="{x_break + 4:.1f}" y="{height - 8}" font-family="sans-serif" font-size="11" fill="#6b645b">2007</text>'
    )
    for points in segments("v1_index"):
        parts.append(f'<polyline fill="none" stroke="#8a8175" stroke-width="1.4" points="{points}"/>')
    for points in segments("w2_index"):
        parts.append(f'<polyline fill="none" stroke="#9a3412" stroke-width="1.6" points="{points}"/>')
    parts.append(
        f'<text x="{width - 210}" y="36" font-family="sans-serif" font-size="12" fill="#9a3412">W2</text>'
    )
    parts.append(
        f'<text x="{width - 180}" y="36" font-family="sans-serif" font-size="12" fill="#8a8175">1.1.1</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


COLUMNS = (
    "date",
    "sample",
    "window",
    "inflation_rate",
    "unemployment_rate",
    "debt_level",
    "debt_observation_date",
    "debt_yoy",
    "debt_qoq",
    "incident_rate",
    "incident_status",
    "homelessness_rate",
    "trust_in_government",
    "vix",
    "nfci",
    "v1_index",
    "v1_band",
    "v1_denominator",
    "w1_index",
    "w1_band",
    "w2_index",
    "w2_band",
    "w2_denominator",
    "w2_qoq_index",
    "w2_qoq_band",
    "w2_nfci_index",
    "w2_nfci_band",
    "w2_episode_band",
    "w2_norm_inflation",
    "w2_norm_unemployment",
    "w2_norm_debt",
    "w2_norm_crime",
    "w2_norm_homelessness",
    "w2_norm_trust",
    "w2_norm_financial",
)

_TWO_DECIMALS = {
    "v1_index",
    "v1_denominator",
    "w1_index",
    "w2_index",
    "w2_denominator",
    "w2_qoq_index",
    "w2_nfci_index",
    "w2_norm_inflation",
    "w2_norm_unemployment",
    "w2_norm_debt",
    "w2_norm_crime",
    "w2_norm_homelessness",
    "w2_norm_trust",
    "w2_norm_financial",
    "homelessness_rate",
}


def csv_fields(row: Mapping) -> dict[str, str]:
    rendered = {}
    for column in COLUMNS:
        if column.startswith("w2_norm_"):
            metric = dict((field, name) for name, field in _NORM_FIELDS)[column]
            value = row["w2_norms"][metric]
        else:
            value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in _TWO_DECIMALS:
            rendered[column] = f"{float(value):.2f}"
        elif isinstance(value, float):
            rendered[column] = format_float(value)
        else:
            rendered[column] = str(value)
    return rendered


SUMMARY_COLUMNS = (
    "scenario",
    "scenario_label",
    "window",
    "window_title",
    "months",
    "min_index",
    "min_date",
    "max_index",
    "max_date",
    "mean_index",
    "stdev_index",
    "high",
    "moderate",
    "low",
    "critical",
)

WEEKLY_COLUMNS = (
    "series",
    "sample",
    "weeks",
    "mean_abs_change",
    "stdev_change",
    "share_flat",
    "max_abs_change",
    "max_abs_week",
    "max_drop",
    "max_drop_week",
)


def _summary_fields(row: Mapping) -> dict[str, str]:
    rendered = {}
    for column in SUMMARY_COLUMNS:
        value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in {"min_index", "max_index", "mean_index", "stdev_index"}:
            rendered[column] = f"{float(value):.2f}"
        else:
            rendered[column] = str(value)
    return rendered


def _weekly_fields(row: Mapping) -> dict[str, str]:
    rendered = {}
    for column in WEEKLY_COLUMNS:
        value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in {"mean_abs_change", "stdev_change", "max_abs_change", "max_drop"}:
            rendered[column] = f"{float(value):.2f}"
        elif column == "share_flat":
            rendered[column] = f"{float(value):.6f}"
        else:
            rendered[column] = str(value)
    return rendered


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def assemble(bundle: Optional[Mapping] = None) -> dict:
    for name, weights in (("W1", W1), ("W2", W2)):
        if round(sum(weights.values()), 10) != 0.72:
            raise ValueError(f"{name} weights sum to {sum(weights.values())}, not 0.72")
    rows, context = build_rows(bundle)
    today = current_reading(context["bundle"], context)
    summary = summarize(rows)
    weekly = weekly_volatility(rows, context["bundle"], context["ends"])
    return {
        "rows": rows,
        "today": today,
        "ends": context["ends"],
        "anchors": context["anchors"],
        "summary": summary,
        "weekly": weekly,
        "pins": context["pins"],
        "ceiling": debt_level_ceiling(context["pins"]),
        "crime": _crime_span(context["bundle"]),
        "debt_stuck": _debt_level_stuck(rows, context["ends"]["debt_level"]["hi"]),
        "recommend": _should_recommend(rows, today),
        "bundle": context["bundle"],
    }


def _debt_level_stuck(rows: Sequence[Mapping], ceiling: float) -> dict:
    """How many replay months sit above the frozen debt-level p98."""
    sample = [row for row in rows if row["sample"] == "out_of_sample" and row["debt_level"] is not None]
    stuck = [row for row in sample if float(row["debt_level"]) > ceiling]
    first = "" if not stuck else str(stuck[0]["date"])
    after = [row for row in sample if first and str(row["date"]) >= first]
    return {
        "months": len(sample),
        "stuck": len(stuck),
        "first": first,
        "all_after_first": bool(after) and all(float(row["debt_level"]) > ceiling for row in after),
    }


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    report = assemble()
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly = output_dir / MONTHLY_NAME
    summary_path = output_dir / SUMMARY_NAME
    weekly_path = output_dir / WEEKLY_NAME
    chart_path = output_dir / CHART_NAME
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    _write_csv(monthly, COLUMNS, [csv_fields(row) for row in report["rows"]])
    _write_csv(summary_path, SUMMARY_COLUMNS, [_summary_fields(row) for row in report["summary"]])
    _write_csv(weekly_path, WEEKLY_COLUMNS, [_weekly_fields(row) for row in report["weekly"]])
    chart_path.write_text(render_svg(report["rows"]), encoding="utf-8")
    note.write_text(render_markdown(report), encoding="utf-8")
    return [monthly, summary_path, weekly_path, chart_path, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.combined_design",
        description=(
            "Replay a research-only combined 2.0 design. Does not change the live score."
        ),
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--note", type=Path, default=None)
    parser.add_argument(
        "--check-locked",
        action="store_true",
        help=f"Print the {PUBLISHED_DATE} six-input score before writing",
    )
    args = parser.parse_args(argv)
    if args.check_locked:
        scored = score_published_inputs(load_published_raws())
        band = interpret(scored["index"])["band"]
        print(f"{PUBLISHED_DATE} {scored['index']:.2f} {band} methodology 1.0.0")
    written = write_outputs(args.output, args.note)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
