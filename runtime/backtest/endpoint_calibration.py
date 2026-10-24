# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Research replay of methodology 1.1.1 under alternate endpoints and bands.

Same six inputs. Same weights. This module does not publish a score and
does not change ``runtime.processing.formula``, the weekly job,
``docs/data/latest.json``, or the weekly history.

The reference window is January 1970 through December 2006. Percentiles
and band anchors are computed on that window and then frozen. They are
not rolling, and the files that feed them stop in 2006.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from calendar import monthrange
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

# Frozen reference window. It contains the 1970s inflation peak and the
# 1982 unemployment peak, and it ends the month before this replay starts.
# It is not refit when a new month arrives.
REFERENCE_START = "1970-01-01"
REFERENCE_END = "2006-12-01"
DEBT_REFERENCE_END = "2006-10-01"
# Named episodes inside the reference window. March 1980 is the CPI
# year-over-year peak. 1995–2006 is the calm end of the same window.
STRESS_MONTH = "1980-03-01"
CALM_START = "1995-01-01"
CALM_END = "2006-12-01"
REPLAY_START = "2007-01-01"
REPLAY_END = "2026-08-01"
CALM_REPLAY_START = "2015-01-01"
CALM_REPLAY_END = "2019-12-01"
CRIME_START = "2018-01-01"
PULL_DATE = "2026-10-12"
DIAGNOSIS_START = "2000-01-01"

PACKAGE_DIR = Path(__file__).resolve().parent
CALIBRATION_DIR = PACKAGE_DIR / "fixtures" / "calibration"
V2_FIXTURE_DIR = PACKAGE_DIR / "fixtures" / "v2"
OUTPUT_DIR = PACKAGE_DIR / "output"
NOTE_NAME = "ENDPOINT_CALIBRATION.md"
MONTHLY_NAME = "endpoint_calibration_monthly.csv"
SUMMARY_NAME = "endpoint_calibration_summary.csv"
WEEKLY_NAME = "endpoint_calibration_weekly.csv"
CHART_NAME = "endpoint_calibration_chart.svg"
ROOT = PACKAGE_DIR.parents[1]
LATEST_PATH = ROOT / "docs" / "data" / "latest.json"

KEY_MONTHS = (
    ("2008-10-01", "Financial stress, unemployment still 6.5"),
    ("2009-10-01", "Unemployment 10.0"),
    ("2020-04-01", "Unemployment 14.8"),
    ("2022-06-01", "Headline CPI peak in this replay"),
    ("2026-08-01", "Last headline CPI month"),
)

SUMMARY_WINDOWS = (
    ("all", "Full history (Jan 2007–Aug 2026)", None, None),
    ("2008", "2008 (Dec 2007–Dec 2009)", "2007-12-01", "2009-12-01"),
    ("2020", "2020", "2020-01-01", "2020-12-01"),
    ("2022", "2022 inflation year", "2022-01-01", "2022-12-01"),
    ("2015_2019", "2015–2019", CALM_REPLAY_START, CALM_REPLAY_END),
)


def percentile(values: Sequence[float], p: float) -> float:
    """Linear percentile. NumPy's type-7 rule, p on a 0–100 scale.

    ``rank = (p/100) * (n - 1)``, then interpolate. One definition, used
    for every endpoint and for the rejected quantile sketch.
    """
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
    return series[max(available)], max(available)


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


def inflation_sample(bundle: Mapping, start: str, end: str) -> list[tuple[str, float]]:
    """Year-over-year CPI. Reference months come from the 2006 file.

    Replay months come from the v2 file. The two files are not mixed
    inside a month.
    """
    points = []
    for day in iter_months(start, end):
        levels = bundle["reference_cpi"] if day <= REFERENCE_END else bundle["replay_cpi"]
        value = _yoy(levels, day)
        if value is not None:
            points.append((day, value))
    return points


def unemployment_sample(bundle: Mapping, start: str, end: str) -> list[tuple[str, float]]:
    points = []
    for day in iter_months(start, end):
        series = (
            bundle["reference_unemployment"] if day <= REFERENCE_END else bundle["replay_unemployment"]
        )
        if day in series:
            points.append((day, series[day]))
    return points


def debt_sample(bundle: Mapping, start: str, end: str) -> list[tuple[str, float]]:
    """Quarter-start prints only. Carried months are not extra observations."""
    series = dict(bundle["reference_debt"])
    for day, value in bundle["replay_debt"].items():
        if day > DEBT_REFERENCE_END:
            series[day] = value
    return [(day, series[day]) for day in sorted(series) if start <= day <= end]


def research_ranges(bundle: Mapping) -> dict[str, tuple[float, float]]:
    """Live endpoints, with three series replaced by frozen p2–p98.

    Crime, homelessness, and trust keep ``METRIC_RANGES``. Crime has no
    fair pre-2018 path. Homelessness and trust are one checklist point
    each, so a percentile endpoint is undefined.
    """
    ranges = dict(METRIC_RANGES)
    inflation = [value for _, value in inflation_sample(bundle, REFERENCE_START, REFERENCE_END)]
    unemployment = [
        value for _, value in unemployment_sample(bundle, REFERENCE_START, REFERENCE_END)
    ]
    debt = [value for _, value in debt_sample(bundle, REFERENCE_START, DEBT_REFERENCE_END)]
    ranges["inflation_rate"] = (percentile(inflation, 2), percentile(inflation, 98))
    ranges["unemployment_rate"] = (percentile(unemployment, 2), percentile(unemployment, 98))
    ranges["debt_to_gdp_ratio"] = (percentile(debt, 2), percentile(debt, 98))
    return ranges


def _score(raws: Mapping[str, Optional[float]], ranges: Mapping[str, tuple]) -> dict:
    """Same aggregation as ``compute_index``, with caller-supplied endpoints.

    Missing inputs drop out. The index uses the unrounded component, then
    rounds to two decimals. This is not a call to ``compute_index`` unless
    ``ranges`` is ``METRIC_RANGES`` and the caller checks that path itself.
    """
    total = 0.0
    weight_sum = 0.0
    norms = {}
    present = []
    for metric in CORE_METRICS:
        raw = raws.get(metric)
        if raw is None or not isinstance(raw, (int, float)):
            norms[metric] = None
            continue
        lo, hi = ranges[metric]
        value = normalize(float(raw), lo, hi, inverse=metric == "trust_in_government")
        norms[metric] = value
        total += value * WEIGHTS[metric]
        weight_sum += WEIGHTS[metric]
        present.append(metric)
    index = round(total / weight_sum, 2) if weight_sum else None
    return {
        "index": index,
        "norms": norms,
        "denominator": weight_sum,
        "present": present,
    }


def _v1_index(raws: Mapping[str, Optional[float]]) -> tuple[Optional[float], Optional[str]]:
    payload = {
        metric: {"data": {metric: raws[metric]}}
        for metric in CORE_METRICS
        if isinstance(raws.get(metric), (int, float))
    }
    if not payload:
        return None, None
    index = compute_index(payload)["index"]
    return index, interpret(index)["band"]


def episode_band(index: float, stress: float, calm: float) -> str:
    """Four bands anchored to two reference-window episodes.

    Critical is strictly worse than the stress month. High is at or above
    the calm-period median. The midpoint splits Low and Moderate.
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
    if _between(day, "2007-12-01", "2009-12-01"):
        return "2008"
    if _between(day, "2020-01-01", "2020-12-01"):
        return "2020"
    if _between(day, "2022-01-01", "2022-12-01"):
        return "2022"
    if _between(day, CALM_REPLAY_START, CALM_REPLAY_END):
        return "2015_2019"
    return "history"


def month_raws(day: str, bundle: Mapping, pins: Mapping[str, float]) -> dict:
    if day <= REFERENCE_END:
        inflation = _yoy(bundle["reference_cpi"], day)
        unemployment = bundle["reference_unemployment"].get(day)
        debt, debt_date = _asof(bundle["reference_debt"], day)
    else:
        inflation = _yoy(bundle["replay_cpi"], day)
        unemployment = bundle["replay_unemployment"].get(day)
        debt, debt_date = _asof(bundle["replay_debt"], day)
    crime, crime_status = _crime_for(bundle["crime"], day)
    return {
        "inflation_rate": inflation,
        "unemployment_rate": unemployment,
        "debt_to_gdp_ratio": debt,
        "debt_observation_date": debt_date,
        "incident_rate": crime,
        "incident_status": crime_status,
        "homelessness_rate": float(pins["homelessness_rate"]),
        "trust_in_government": float(pins["trust_in_government"]),
    }


def _anchors(bundle: Mapping, ranges: Mapping[str, tuple], pins: Mapping) -> dict:
    """Stress month and calm-period median, on one endpoint set."""
    indexes = []
    stress_index = None
    for day in iter_months(REFERENCE_START, REFERENCE_END):
        scored = _score(month_raws(day, bundle, pins), ranges)
        index = scored["index"]
        if day == STRESS_MONTH:
            stress_index = index
        if index is not None and _between(day, CALM_START, CALM_END):
            indexes.append(index)
    if stress_index is None or not indexes:
        raise ValueError("reference window did not produce band anchors")
    return {"stress": float(stress_index), "calm": percentile(indexes, 50)}


def build_rows(bundle: Optional[Mapping] = None) -> tuple[list[dict], dict]:
    """One replay row per month, plus the frozen ranges and band anchors."""
    bundle = load_bundle() if bundle is None else bundle
    pins = checklist_pins()
    ranges = research_ranges(bundle)
    live_anchors = _anchors(bundle, METRIC_RANGES, pins)
    research_anchors = _anchors(bundle, ranges, pins)
    rows = []
    for day in iter_months(REPLAY_START, REPLAY_END):
        raws = month_raws(day, bundle, pins)
        v1_index, v1_band = _v1_index(raws)
        live = _score(raws, METRIC_RANGES)
        widened = _score(raws, ranges)
        if live["index"] != v1_index:
            raise ValueError(f"{day}: live endpoints drifted from compute_index")
        a_band = None if widened["index"] is None else interpret(widened["index"])["band"]
        rows.append(
            {
                "date": day,
                "window": _window_name(day),
                "inflation_rate": raws["inflation_rate"],
                "unemployment_rate": raws["unemployment_rate"],
                "debt_to_gdp_ratio": raws["debt_to_gdp_ratio"],
                "debt_observation_date": raws["debt_observation_date"],
                "incident_rate": raws["incident_rate"],
                "incident_status": raws["incident_status"],
                "homelessness_rate": raws["homelessness_rate"],
                "trust_in_government": raws["trust_in_government"],
                "v1_index": v1_index,
                "v1_band": v1_band,
                "v1_denominator": live["denominator"],
                "v1_norms": live["norms"],
                "a_index": widened["index"],
                "a_band": a_band,
                "a_norms": widened["norms"],
                "b_band": (
                    None
                    if v1_index is None
                    else episode_band(v1_index, live_anchors["stress"], live_anchors["calm"])
                ),
                "c_band": (
                    None
                    if widened["index"] is None
                    else episode_band(
                        widened["index"], research_anchors["stress"], research_anchors["calm"]
                    )
                ),
            }
        )
    context = {
        "ranges": ranges,
        "live_anchors": live_anchors,
        "research_anchors": research_anchors,
        "pins": pins,
        "bundle": bundle,
    }
    return rows, context


def current_reading(bundle: Optional[Mapping] = None, context: Optional[Mapping] = None) -> dict:
    """1.1.1 restatement of the committed latest.json raws. Does not write the file."""
    bundle = load_bundle() if bundle is None else bundle
    if context is None:
        _, context = build_rows(bundle)
    latest = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    pins = context["pins"]
    published = {metric: float(latest["metrics"][metric]["raw"]) for metric in CORE_METRICS}
    published_index, published_band = _v1_index(published)
    restated = dict(published)
    restated["homelessness_rate"] = float(pins["homelessness_rate"])
    restated["trust_in_government"] = float(pins["trust_in_government"])
    restated["debt_observation_date"] = latest["metrics"]["debt_to_gdp_ratio"]["observation_date"]
    restated["incident_status"] = "published"
    v1_index, v1_band = _v1_index(restated)
    live = _score(restated, METRIC_RANGES)
    widened = _score(restated, context["ranges"])
    return {
        "publication_date": str(latest["publication_date"]),
        "published_methodology": latest["methodology_version"],
        "published_file_index": latest["bugout_index"],
        "published_index": published_index,
        "published_band": published_band,
        "date": str(latest["publication_date"]),
        "inflation_rate": restated["inflation_rate"],
        "unemployment_rate": restated["unemployment_rate"],
        "debt_to_gdp_ratio": restated["debt_to_gdp_ratio"],
        "incident_rate": restated["incident_rate"],
        "homelessness_rate": restated["homelessness_rate"],
        "trust_in_government": restated["trust_in_government"],
        "inflation_date": latest["metrics"]["inflation_rate"]["observation_date"],
        "unemployment_date": latest["metrics"]["unemployment_rate"]["observation_date"],
        "v1_index": v1_index,
        "v1_band": v1_band,
        "v1_norms": live["norms"],
        "a_index": widened["index"],
        "a_band": interpret(widened["index"])["band"],
        "a_norms": widened["norms"],
        "b_band": episode_band(
            v1_index, context["live_anchors"]["stress"], context["live_anchors"]["calm"]
        ),
        "c_band": episode_band(
            widened["index"],
            context["research_anchors"]["stress"],
            context["research_anchors"]["calm"],
        ),
    }


def _diagnosis(bundle: Mapping) -> list[dict]:
    """How much of each live 0–100 scale the observed sample actually visits."""
    specs = (
        (
            "inflation_rate",
            "Headline CPI YoY",
            [value for _, value in inflation_sample(bundle, DIAGNOSIS_START, REPLAY_END)],
            False,
        ),
        (
            "unemployment_rate",
            "Unemployment",
            [value for _, value in unemployment_sample(bundle, DIAGNOSIS_START, REPLAY_END)],
            False,
        ),
        (
            "debt_to_gdp_ratio",
            "Debt-to-GDP",
            [value for _, value in debt_sample(bundle, DIAGNOSIS_START, "2026-01-01")],
            False,
        ),
        (
            "incident_rate",
            "Crime, Nationwide Full Sample",
            list(bundle["crime"].values()),
            False,
        ),
    )
    rows = []
    for metric, label, values, inverse in specs:
        lo, hi = METRIC_RANGES[metric]
        norms = [normalize(value, lo, hi, inverse=inverse) for value in values]
        rows.append(
            {
                "metric": metric,
                "label": label,
                "n": len(values),
                "raw_min": min(values),
                "raw_max": max(values),
                "lo": lo,
                "hi": hi,
                "norm_min": min(norms),
                "norm_max": max(norms),
                "scale_used": (max(norms) - min(norms)) / 100.0,
                "sample": "2000–2026" if metric != "incident_rate" else "2018–2026",
            }
        )
    pins = checklist_pins()
    for metric, label in (
        ("homelessness_rate", "Homelessness"),
        ("trust_in_government", "Trust in government"),
    ):
        lo, hi = METRIC_RANGES[metric]
        raw = float(pins[metric])
        norm = normalize(raw, lo, hi, inverse=metric == "trust_in_government")
        rows.append(
            {
                "metric": metric,
                "label": label,
                "n": 1,
                "raw_min": raw,
                "raw_max": raw,
                "lo": lo,
                "hi": hi,
                "norm_min": norm,
                "norm_max": norm,
                "scale_used": 0.0,
                "sample": "checklist only",
            }
        )
    return rows


def _short_window_percentiles(bundle: Mapping) -> dict[str, tuple[float, float]]:
    """2000–2006 p2–p98. Reported so the shorter window is visible, and not used."""
    return {
        "inflation_rate": _pair(inflation_sample(bundle, "2000-01-01", REFERENCE_END)),
        "unemployment_rate": _pair(unemployment_sample(bundle, "2000-01-01", REFERENCE_END)),
        "debt_to_gdp_ratio": _pair(debt_sample(bundle, "2000-01-01", DEBT_REFERENCE_END)),
    }


def _pair(points: Sequence[tuple[str, float]]) -> tuple[float, float]:
    values = [value for _, value in points]
    return percentile(values, 2), percentile(values, 98)


def _band_counts(bands: Sequence[Optional[str]]) -> dict[str, int]:
    counts = {
        "High Stability": 0,
        "Moderate Stability": 0,
        "Low Stability": 0,
        "Critical Instability": 0,
    }
    for band in bands:
        if band in counts:
            counts[band] += 1
    return counts


def summarize(rows: Sequence[Mapping]) -> list[dict]:
    summary = []
    scenarios = (
        ("v1", "v1_index", "v1_band", "1.1.1 endpoints and bands"),
        ("a", "a_index", "a_band", "A: p2–p98 endpoints, live bands"),
        ("b", "v1_index", "b_band", "B: live endpoints, episode bands"),
        ("c", "a_index", "c_band", "C: p2–p98 endpoints and episode bands"),
    )
    for window_name, title, start, end in SUMMARY_WINDOWS:
        if start is None:
            subset = list(rows)
        else:
            subset = [row for row in rows if start <= str(row["date"]) <= end]
        for scenario, index_key, band_key, label in scenarios:
            indexes = [row[index_key] for row in subset if row[index_key] is not None]
            counts = _band_counts([row[band_key] for row in subset if row[index_key] is not None])
            order = sorted(
                ((row[index_key], str(row["date"])) for row in subset if row[index_key] is not None)
            )
            summary.append(
                {
                    "scenario": scenario,
                    "scenario_label": label,
                    "window": window_name,
                    "window_title": title,
                    "months": len(indexes),
                    "min_index": None if not order else order[0][0],
                    "min_date": "" if not order else order[0][1],
                    "max_index": None if not order else order[-1][0],
                    "max_date": "" if not order else order[-1][1],
                    "high": counts["High Stability"],
                    "moderate": counts["Moderate Stability"],
                    "low": counts["Low Stability"],
                    "critical": counts["Critical Instability"],
                }
            )
    return summary


def _fridays(start: str, end: str) -> list[str]:
    year, month, day = (int(part) for part in start.split("-"))
    cursor = date(year, month, day)
    end_year, end_month = int(end[:4]), int(end[5:7])
    last = date(end_year, end_month, monthrange(end_year, end_month)[1])
    while cursor.weekday() != 4:
        cursor += timedelta(days=1)
    stamps = []
    while cursor <= last:
        stamps.append(cursor.isoformat())
        cursor += timedelta(days=7)
    return stamps


def weekly_volatility(rows: Sequence[Mapping]) -> list[dict]:
    """Friday-to-Friday moves. Every option is constant inside a month.

    The inputs are monthly or slower. A Friday step that is not zero is a
    new month's print, not an intraweek tick.
    """
    by_month = {str(row["date"]): row for row in rows}
    stamps = [
        stamp
        for stamp in _fridays(REPLAY_START, REPLAY_END)
        if stamp[:7] + "-01" in by_month
    ]
    series = {
        "v1": [(stamp, stamp[:7] + "-01", by_month[stamp[:7] + "-01"]["v1_index"]) for stamp in stamps],
        "a": [(stamp, stamp[:7] + "-01", by_month[stamp[:7] + "-01"]["a_index"]) for stamp in stamps],
    }
    samples = {
        "within_month": lambda prev, cur: prev[1] == cur[1],
        "all_fridays": lambda prev, cur: True,
    }
    output = []
    for name, points in series.items():
        usable = [(stamp, month, index) for stamp, month, index in points if index is not None]
        for sample, predicate in samples.items():
            deltas = []
            for prev, cur in zip(usable, usable[1:]):
                if predicate(prev, cur):
                    deltas.append((cur[0], round(float(cur[2]) - float(prev[2]), 2)))
            output.append(_delta_summary(name, sample, deltas))
    return output


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


def _band_changes(rows: Sequence[Mapping], band_key: str) -> int:
    changes = 0
    previous = None
    for row in rows:
        band = row[band_key]
        if previous is not None and band != previous:
            changes += 1
        previous = band
    return changes


COLUMNS = (
    "date",
    "window",
    "inflation_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "debt_observation_date",
    "incident_rate",
    "incident_status",
    "homelessness_rate",
    "trust_in_government",
    "v1_index",
    "v1_band",
    "v1_denominator",
    "a_index",
    "a_band",
    "b_band",
    "c_band",
)

_TWO_DECIMALS = {"v1_index", "v1_denominator", "a_index", "homelessness_rate"}


def csv_fields(row: Mapping) -> dict[str, str]:
    rendered = {}
    for column in COLUMNS:
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


def _num(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.{digits}f}"


def _cell(index: object, band: object) -> str:
    if index is None:
        return "—"
    short = str(band or "").replace(" Stability", "").replace(" Instability", "")
    return f"{_num(index)} {short}".strip()


def _by_date(rows: Sequence[Mapping]) -> dict[str, Mapping]:
    return {str(row["date"]): row for row in rows}


def _lookup(summary: Sequence[Mapping], scenario: str, window: str) -> Mapping:
    for row in summary:
        if row["scenario"] == scenario and row["window"] == window:
            return row
    raise KeyError((scenario, window))


def _weekly(weekly: Sequence[Mapping], series: str, sample: str) -> Mapping:
    for row in weekly:
        if row["series"] == series and row["sample"] == sample:
            return row
    raise KeyError((series, sample))


def render_markdown(
    rows: Sequence[Mapping],
    summary: Sequence[Mapping],
    weekly: Sequence[Mapping],
    current: Mapping,
    context: Mapping,
) -> str:
    """Results note. Figures come from the rows just scored."""
    by_date = _by_date(rows)
    ranges = context["ranges"]
    pins = context["pins"]
    diagnosis = _diagnosis(context["bundle"])
    short = _short_window_percentiles(context["bundle"])
    live_anchors = context["live_anchors"]
    research_anchors = context["research_anchors"]
    reference_indexes = []
    for day in iter_months(REFERENCE_START, REFERENCE_END):
        scored = _score(month_raws(day, context["bundle"], pins), METRIC_RANGES)
        if scored["index"] is not None:
            reference_indexes.append(scored["index"])
    rejected = (
        percentile(reference_indexes, 80),
        percentile(reference_indexes, 40),
        percentile(reference_indexes, 15),
    )

    def reading_row(label: str, row: Mapping) -> str:
        return (
            f"| {label} | {_cell(row['v1_index'], row['v1_band'])} | "
            f"{_cell(row['a_index'], row['a_band'])} | "
            f"{_cell(row['v1_index'], row['b_band'])} | "
            f"{_cell(row['a_index'], row['c_band'])} |"
        )

    comparison = [
        "| Reading | v1 1.1.1 | A percentile endpoints | B episode bands | C endpoints and bands |",
        "| --- | --- | --- | --- | --- |",
        reading_row(f"Current ({current['publication_date']} inputs, 1.1.1 checklist)", current),
    ]
    for day, reason in KEY_MONTHS:
        comparison.append(reading_row(f"{day} — {reason}", by_date[day]))

    diagnosis_lines = [
        "| Input | Sample | Observed raw range | Live endpoints | Normalized range visited | Share of 0–100 used | Weight |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in diagnosis:
        diagnosis_lines.append(
            "| {label} | {sample} (n={n}) | {raw_lo} to {raw_hi} | {lo} to {hi} | {norm_lo} to {norm_hi} | {used} | {weight} |".format(
                label=item["label"],
                sample=item["sample"],
                n=item["n"],
                raw_lo=_num(item["raw_min"], 2),
                raw_hi=_num(item["raw_max"], 2),
                lo=_num(item["lo"], 2),
                hi=_num(item["hi"], 2),
                norm_lo=_num(item["norm_min"]),
                norm_hi=_num(item["norm_max"]),
                used=_num(item["scale_used"] * 100, 1) + "%",
                weight=_num(WEIGHTS[item["metric"]], 2),
            )
        )

    band_lines = [
        "| Window | Option | High | Moderate | Low | Critical |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    range_lines = [
        "| Window | v1 and B (same index) | A and C (same index) |",
        "| --- | --- | --- |",
    ]
    for window_name, title, _, _ in SUMMARY_WINDOWS:
        v1 = _lookup(summary, "v1", window_name)
        widened = _lookup(summary, "a", window_name)
        range_lines.append(
            f"| {title} | {_num(v1['min_index'])} ({v1['min_date']}) to {_num(v1['max_index'])} ({v1['max_date']}) | "
            f"{_num(widened['min_index'])} ({widened['min_date']}) to {_num(widened['max_index'])} ({widened['max_date']}) |"
        )
        for scenario, label in (("v1", "v1"), ("a", "A"), ("b", "B"), ("c", "C")):
            item = _lookup(summary, scenario, window_name)
            band_lines.append(
                f"| {title} | {label} | {item['high']} | {item['moderate']} | {item['low']} | {item['critical']} |"
            )

    weekly_lines = [
        "| Series | Sample | Weeks | Mean abs move | Stdev of move | Share flat | Largest move | Largest drop |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for series, label in (("v1", "v1 and B"), ("a", "A and C")):
        for sample in ("within_month", "all_fridays"):
            item = _weekly(weekly, series, sample)
            weekly_lines.append(
                "| {label} | {sample} | {n} | {mean} | {dev} | {flat} | {big} ({when}) | {drop} ({dwhen}) |".format(
                    label=label,
                    sample=sample,
                    n=item["weeks"],
                    mean=_num(item["mean_abs_change"], 2),
                    dev=_num(item["stdev_change"], 2),
                    flat=_num(float(item["share_flat"]) * 100, 1) + "%" if item["share_flat"] is not None else "—",
                    big=_num(item["max_abs_change"]),
                    when=item["max_abs_week"] or "—",
                    drop=_num(item["max_drop"]),
                    dwhen=item["max_drop_week"] or "—",
                )
            )

    oct_2008 = by_date["2008-10-01"]
    oct_2009 = by_date["2009-10-01"]
    apr_2020 = by_date["2020-04-01"]
    jun_2022 = by_date["2022-06-01"]
    debt_hi = ranges["debt_to_gdp_ratio"][1]
    debt_clamped = sum(
        1
        for row in rows
        if row["debt_to_gdp_ratio"] is not None and float(row["debt_to_gdp_ratio"]) >= debt_hi
    )
    first_clamp = next(
        row["date"]
        for row in rows
        if row["debt_to_gdp_ratio"] is not None and float(row["debt_to_gdp_ratio"]) >= debt_hi
    )
    # Best case while debt is on the stressed endpoint and the checklist is unchanged.
    ceiling_raws = {
        "inflation_rate": ranges["inflation_rate"][0],
        "unemployment_rate": ranges["unemployment_rate"][0],
        "debt_to_gdp_ratio": debt_hi,
        "incident_rate": METRIC_RANGES["incident_rate"][0],
        "homelessness_rate": float(pins["homelessness_rate"]),
        "trust_in_government": float(pins["trust_in_government"]),
    }
    ceiling = _score(ceiling_raws, ranges)["index"]
    v1_all = _lookup(summary, "v1", "all")
    a_all = _lookup(summary, "a", "all")
    b_all = _lookup(summary, "b", "all")
    c_all = _lookup(summary, "c", "all")
    a_calm = _lookup(summary, "a", "2015_2019")
    v1_within = _weekly(weekly, "v1", "within_month")
    a_all_fridays = _weekly(weekly, "a", "all_fridays")
    v1_all_fridays = _weekly(weekly, "v1", "all_fridays")

    def _largest_complete_step(index_key: str) -> tuple[float, str]:
        best_delta = 0.0
        best_day = ""
        for previous, current_row in zip(rows, rows[1:]):
            if previous["inflation_rate"] is None or current_row["inflation_rate"] is None:
                continue
            if previous["unemployment_rate"] is None or current_row["unemployment_rate"] is None:
                continue
            delta = round(float(current_row[index_key]) - float(previous[index_key]), 2)
            if best_day == "" or abs(delta) > abs(best_delta):
                best_delta = delta
                best_day = str(current_row["date"])
        return best_delta, best_day

    complete_a = _largest_complete_step("a_index")
    complete_v1 = _largest_complete_step("v1_index")
    b_high_dates = [str(row["date"]) for row in rows if row["b_band"] == "High Stability"]
    b_high_span = (
        "none"
        if not b_high_dates
        else f"{b_high_dates[0]} through {b_high_dates[-1]}"
    )

    text = f"""# Endpoint and band calibration (research)

Research only. This note is not a methodology version. It does not change `compute_index`, methodology 1.1.1, `docs/data/latest.json`, or the weekly history. The six inputs and the six weights stay as they are. Pew trust, Gallup confidence, and the shelter companions stay outside the score.

**Stay on methodology 1.1.1.** Do not publish a recalibrated scale from this replay.

October 2008 scores **{_cell(oct_2008['v1_index'], oct_2008['v1_band'])}** and the current 1.1.1 restatement scores **{_cell(current['v1_index'], current['v1_band'])}**. The gap is **{_num(float(current['v1_index']) - float(oct_2008['v1_index']))}** points. The live index from January 2007 through August 2026 runs **{_num(v1_all['min_index'])}** to **{_num(v1_all['max_index'])}**. High and Critical do not occur. A cutoff between those two scores would sit inside ordinary month-to-month movement. Stretching the endpoints can split them, and the stretch that does it pins debt at the stressed end from {first_clamp} onward. While debt sits there, High Stability is out of reach: the best remaining inputs still score **{_num(ceiling)}**, under the live High line of 70. The combination that then calls today High does it with debt already maxed out.

Read this file. You do not need to run the harness. Month-by-month numbers are in [`output/endpoint_calibration_monthly.csv`](output/endpoint_calibration_monthly.csv). Window counts are in [`output/endpoint_calibration_summary.csv`](output/endpoint_calibration_summary.csv). Friday moves are in [`output/endpoint_calibration_weekly.csv`](output/endpoint_calibration_weekly.csv). The chart is [`output/endpoint_calibration_chart.svg`](output/endpoint_calibration_chart.svg).

The 19 September 2026 published row still scores **57.11 Moderate** through `compute_index` under methodology 1.0.0. The committed `latest.json` is the {current['publication_date']} week, methodology {current['published_methodology']}, index **{_num(current['published_file_index'])}**. Scoring those six published raws returns **{_num(current['published_index'])}**. This replay does not rewrite that file. The 1.1.1 column changes only homelessness to **{_num(pins['homelessness_rate'], 2)}** and trust to **{_num(pins['trust_in_government'], 0)}**.

## What compresses the index

Live endpoints and the sample that actually showed up. Inflation, unemployment, and debt are January 2000 through the latest print in this pull. Crime is the RTCI file, January 2018 through April 2026. Homelessness and trust are the 1.1.1 checklist, one point each. "Share of 0–100 used" is the gap between the lowest and highest normalized score divided by 100.

{chr(10).join(diagnosis_lines)}

Homelessness and trust are **{_num(WEIGHTS['homelessness_rate'] + WEIGHTS['trust_in_government'], 2)}** of the **0.72** weight, and they do not move. That is **{_num(100 * (WEIGHTS['homelessness_rate'] + WEIGHTS['trust_in_government']) / sum(WEIGHTS.values()), 1)}%** of the index sitting on a fixed contribution (homelessness **{_num(diagnosis[4]['norm_min'])}**, trust **{_num(diagnosis[5]['norm_min'])}**). Crime's observed rates, about **{_num(diagnosis[3]['raw_min'], 0)}** to **{_num(diagnosis[3]['raw_max'], 0)}**, use **{_num(diagnosis[3]['scale_used'] * 100, 1)}%** of the 500–8,000 scale and normalize into a band about **{_num(diagnosis[3]['norm_min'])}** to **{_num(diagnosis[3]['norm_max'])}**. Inflation, unemployment, and debt each visit under half of their 0–100 scale. The index is the weighted average of a narrow middle.

October 2008 and today land on top of each other because the components trade places. Unemployment was **{_num(oct_2008['unemployment_rate'], 1)}** then and is **{_num(current['unemployment_rate'], 1)}** now (normalized **{_num(oct_2008['v1_norms']['unemployment_rate'])}** then, **{_num(current['v1_norms']['unemployment_rate'])}** now). Debt was **{_num(oct_2008['debt_to_gdp_ratio'])}** then and is **{_num(current['debt_to_gdp_ratio'])}** now (normalized **{_num(oct_2008['v1_norms']['debt_to_gdp_ratio'])}** then, **{_num(current['v1_norms']['debt_to_gdp_ratio'])}** now). Inflation is nearly the same print. Crime is absent in October 2008, so that month's denominator is **{_num(oct_2008['v1_denominator'])}**. Today's crime print normalizes to **{_num(current['v1_norms']['incident_rate'])}** and the denominator is **0.72**. The labor improvement and the calm crime print are offset by the debt deterioration. No band edge placed between **{_num(oct_2008['v1_index'])}** and **{_num(current['v1_index'])}** describes a different regime. It describes a rounding choice. The largest month-to-month step on the live index is **{_num(v1_all_fridays['max_abs_change'])}**, on the week of {v1_all_fridays['max_abs_week']}.

## The three options

Weights stay at inflation 0.15, crime 0.12, unemployment 0.12, debt 0.12, homelessness 0.09, trust 0.12. Missing inputs still drop out.

The reference window is **{REFERENCE_START} through {REFERENCE_END}** (debt through **{DEBT_REFERENCE_END}**, the last quarter in that window). Percentiles use the type-7 rule: rank `(p/100) × (n − 1)`, then linear interpolation. The window is fixed. It is not a trailing window, and it is not refit on 2008, 2020, or 2022.

A shorter window, January 2000 through December 2006, is the Great Moderation in these files: inflation p2–p98 **{_num(short['inflation_rate'][0], 2)}** to **{_num(short['inflation_rate'][1], 2)}**, unemployment **{_num(short['unemployment_rate'][0], 2)}** to **{_num(short['unemployment_rate'][1], 2)}**, debt **{_num(short['debt_to_gdp_ratio'][0], 2)}** to **{_num(short['debt_to_gdp_ratio'][1], 2)}**. Those endpoints would clamp almost every later month. They are not used.

**Option A** replaces three endpoints with the reference window's 2nd and 98th percentiles. The calm end is p2 and the stressed end is p98, because higher inflation, unemployment, and debt are less stable. Crime stays 500–8,000. Homelessness stays 0–0.5. Trust stays 0–80, inverted. Bands stay the live `interpret` cutoffs: High at or above 70, Moderate at or above 55, Low at or above 40, Critical below 40.

| Input | Live endpoints | Option A endpoints |
| --- | --- | --- |
| Headline CPI YoY | {_num(METRIC_RANGES['inflation_rate'][0], 0)} to {_num(METRIC_RANGES['inflation_rate'][1], 0)} | {_num(ranges['inflation_rate'][0], 2)} to {_num(ranges['inflation_rate'][1], 2)} |
| Unemployment | {_num(METRIC_RANGES['unemployment_rate'][0], 0)} to {_num(METRIC_RANGES['unemployment_rate'][1], 0)} | {_num(ranges['unemployment_rate'][0], 2)} to {_num(ranges['unemployment_rate'][1], 2)} |
| Debt-to-GDP | {_num(METRIC_RANGES['debt_to_gdp_ratio'][0], 0)} to {_num(METRIC_RANGES['debt_to_gdp_ratio'][1], 0)} | {_num(ranges['debt_to_gdp_ratio'][0], 2)} to {_num(ranges['debt_to_gdp_ratio'][1], 2)} |
| Crime | 500 to 8,000 | unchanged |
| Homelessness | 0 to 0.5 | unchanged |
| Trust | 0 to 80, inverted | unchanged |

**Option B** keeps the live endpoints and moves the bands to two named episodes inside the reference window, scored with the live endpoints and the same held checklist. There is no crime series in that window, so the denominator is 0.60.

- Stress anchor: **{STRESS_MONTH}**, the reference window's CPI year-over-year peak. The live-endpoint index that month is **{_num(live_anchors['stress'])}**. Critical is strictly below that index. November 1982, the unemployment peak in this file, scores higher than March 1980 on the live formula, because inflation had already fallen. The inflation peak is the lower anchor.
- Calm anchor: the median monthly index from **{CALM_START}** through **{CALM_END}**, **{_num(live_anchors['calm'])}**. High is at or above that median.
- The midpoint, **{_num((live_anchors['stress'] + live_anchors['calm']) / 2)}**, splits Low and Moderate.

A quantile rule on the same reference index was inspected and not used. The reference index itself only runs from the high 40s to the low 60s, so p80 / p40 / p15 are **{_num(rejected[0])}** / **{_num(rejected[1])}** / **{_num(rejected[2])}**. October 2008 at **{_num(oct_2008['v1_index'])}** and today at **{_num(current['v1_index'])}** both fall between p15 and p40. The tighter cuts manufacture Critical months without splitting the pair the question is about.

**Option C** uses option A's endpoints and the same episode rule scored on those endpoints. The March 1980 index is **{_num(research_anchors['stress'])}**. The 1995–2006 median is **{_num(research_anchors['calm'])}**. The midpoint is **{_num((research_anchors['stress'] + research_anchors['calm']) / 2)}**.

## Readings

The current row uses the published {current['publication_date']} raws for inflation ({current['inflation_date']}), unemployment ({current['unemployment_date']}), debt, and crime, and the 1.1.1 checklist for homelessness and trust. August 2026 in the monthly file is a different unemployment print (**{_num(by_date['2026-08-01']['unemployment_rate'], 1)}**, not **{_num(current['unemployment_rate'], 1)}**).

{chr(10).join(comparison)}

B prints the v1 index with a different band. C prints the option A index with a different band. The number does not move unless the endpoints move.

{chr(10).join(range_lines)}

{chr(10).join(band_lines)}

Full-history band totals: v1 is **{v1_all['high']}** High and **{v1_all['critical']}** Critical. A is **{a_all['high']}** High and **{a_all['critical']}** Critical. B is **{b_all['high']}** High and **{b_all['critical']}** Critical. C is **{c_all['high']}** High and **{c_all['critical']}** Critical. Month-to-month band changes: v1 **{_band_changes(rows, 'v1_band')}**, A **{_band_changes(rows, 'a_band')}**, B **{_band_changes(rows, 'b_band')}**, C **{_band_changes(rows, 'c_band')}**.

### Do 2008 and 2020 separate from the calm years?

2015–2019 is the calm stretch in this replay: unemployment at or below the mid-4s for long stretches, inflation mostly under 3, crime in the file.

On v1, 2015–2019 is entirely Moderate. The 2008 window is 23 Moderate and 2 Low. October 2008 itself is Moderate, like today. 2020 is 8 Moderate and 4 Low. 2022 is 12 Low. 2022 separates from today. October 2008 does not.

On A, 2015–2019 is entirely Moderate, from **{_num(a_calm['min_index'])}** to **{_num(a_calm['max_index'])}**. October 2008 is **{_cell(oct_2008['a_index'], oct_2008['a_band'])}**. October 2009 is **{_cell(oct_2009['a_index'], oct_2009['a_band'])}**. April 2020 is **{_cell(apr_2020['a_index'], apr_2020['a_band'])}**. June 2022 is **{_cell(jun_2022['a_index'], jun_2022['a_band'])}**. Today is **{_cell(current['a_index'], current['a_band'])}**. Those four stress months are Low and today is Moderate. That is the separation. Critical still does not fire. The sample low on A is **{_num(a_all['min_index'])}** on {a_all['min_date']}, just above 40.

On B, October 2008 and today are both Moderate. The March 1980 anchor at **{_num(live_anchors['stress'])}** is below every month in the replay (the replay low is **{_num(v1_all['min_index'])}**), so Critical does not fire. B's **{b_all['high']}** High months run {b_high_span}, the prints above the 1995–2006 median. The episode bands sit next to the live 55 / 40 cutoffs and do not answer the question.

On C, October 2008, October 2009, April 2020, and June 2022 are Critical, and today is **{str(current['c_band']).replace(' Stability', '')}**. The other eleven months of 2022 are Low. 2015–2019 is **{_lookup(summary, 'c', '2015_2019')['high']}** High and **{_lookup(summary, 'c', '2015_2019')['moderate']}** Moderate. Critical is **{c_all['critical']}** of **{c_all['months']}** months. The word on the live scale for that band is Collapse Likely.

### Why A separates, and what it stops seeing

Option A's debt endpoint tops out at **{_num(debt_hi, 2)}**. The replay's debt print reaches that on **{first_clamp}** and stays at or above it for **{debt_clamped}** of **{len(rows)}** months. July 2008 through the present is one debt score: the stressed end. Further increases, from about 67 to today's **{_num(current['debt_to_gdp_ratio'])}**, do not move the index. The gap between October 2008 and today then comes from unemployment (normalized **{_num(oct_2008['a_norms']['unemployment_rate'])}** then, **{_num(current['a_norms']['unemployment_rate'])}** now) and from inflation, which looks calmer on a scale whose stressed end is the 1970s rather than 15. October 2009 inflation was **{_num(oct_2009['inflation_rate'], 2)}**, below the p2 endpoint, so it clamps at fully stable and the unemployment print does the work of pulling that month down.

The ceiling while debt is on that endpoint, homelessness and trust stay on the checklist, and inflation, unemployment, and crime are all at their most stable endpoint, is **{_num(ceiling)}**. Live High is 70. High does not just fail to show up in this sample. It cannot show up until debt-to-GDP falls back through **{_num(debt_hi, 2)}** or the checklist changes.

Crime is still compressed, because its endpoints were not refit. There is no 1970–2006 RTCI sample to refit them from.

## Weekly volatility

Within a calendar month the index does not move. Across **{v1_within['weeks']}** within-month Friday pairs, v1, A, B, and C are flat on every pair (share flat **{_num(float(v1_within['share_flat']) * 100, 1)}%**). B uses the v1 index. C uses the A index. Changing bands does not add a weekly tick.

Across all Fridays, including the step into a new month, the mean absolute move is **{_num(v1_all_fridays['mean_abs_change'], 2)}** on v1 and **{_num(a_all_fridays['mean_abs_change'], 2)}** on A. The largest A step in the Friday file is **{_num(a_all_fridays['max_abs_change'])}** on the week of {a_all_fridays['max_abs_week']}, and the largest drop is **{_num(a_all_fridays['max_drop'])}** on the week of {a_all_fridays['max_drop_week']}. Those two steps are the October 2025 blank, when CPI and unemployment are missing, and the return of both series the next month. Option A falls from **{_num(by_date['2025-09-01']['a_index'])}** to **{_num(by_date['2025-10-01']['a_index'])}** and back to **{_num(by_date['2025-11-01']['a_index'])}**. That is a missing-input month, not a weekly shock. Among months that keep inflation and unemployment, the largest A step is **{_num(complete_a[0])}** into {complete_a[1]}, and the largest v1 step is **{_num(complete_v1[0])}** into {complete_v1[1]}. The shorter unemployment and inflation scales turn that labor print into a larger index step. This path is the revised vintage, not the print that was public on that Friday.

{chr(10).join(weekly_lines)}

## If this were a version

It would be **methodology 2.0.0**, not 1.2.0. Endpoints are what a point on the 0–100 scale means. Option C would also change what Moderate means. A 57.50 Moderate under 1.1.1 is not a revision of a different number under new endpoints, and the new number is not a revision of 57.50.

The weekly history would keep each row's `methodology_version`. Rows through the last 1.1.1 week would stay 1.1.1. The first 2.0.0 week would be a break in the chart, with one sentence next to it: the scale changed, and the old number is still the old number. `latest.json` would carry 2.0.0 from that week forward. It would not be rewritten backward. The release note would name the reference window, the percentile rule, and the three endpoints that moved, and it would say that crime, homelessness, and trust were left alone because they have no matching history.

This replay does not cut that version.

## What was not adopted

- Option B does not separate October 2008 from today. The live scores are too close, and the 1980 anchor is below the whole replay.
- Option A does separate the stress months from today, and it makes High unreachable for as long as debt-to-GDP stays above the 1970–2006 98th percentile. Debt stops ranking months after {first_clamp}.
- Option C separates them by calling a large share of the replay Critical, Collapse Likely, and by calling the current reading High while debt is on the stressed endpoint.
- Crime, homelessness, and trust still have nothing in the reference window to recalibrate. Together with a clamped debt input, most of the weight is a constant.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.endpoint_calibration --check-locked
```

That reprints the locked 57.11 line and the 1.1.1 restatement, and rewrites the CSV files, this note, and the chart. It does not run the weekly publisher.

`python -m runtime.backtest` remains the v1.0.0-only replay. The v2 candidate command is a different research question and is unchanged.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
"""
    return text


def render_svg(rows: Sequence[Mapping]) -> str:
    """Full history and three stress windows. v1 and option A only.

    B shares the v1 line. C shares the A line.
    """
    width = 760
    height = 210
    left = 48
    right = 16
    top = 28
    bottom = 36
    colors = {"v1_index": "#1d4e89", "a_index": "#b45309"}
    panels_spec = (
        ("all", "Full history"),
        ("2008", "2008 window"),
        ("2020", "2020"),
        ("2022", "2022"),
    )
    y_lo, y_hi = 35.0, 80.0
    parts = []
    for index, (window_name, title) in enumerate(panels_spec):
        if window_name == "all":
            subset = list(rows)
        else:
            subset = [row for row in rows if row["window"] == window_name]
        origin_y = index * height
        plot_w = width - left - right
        plot_h = height - top - bottom
        parts.append(
            f'<text x="{left}" y="{origin_y + 18}" font-family="sans-serif" font-size="13">{title}</text>'
        )
        base_y = origin_y + top + plot_h
        parts.append(
            f'<line x1="{left}" y1="{base_y}" x2="{width - right}" y2="{base_y}" stroke="#d0d0d0"/>'
        )
        for guide in (40, 55, 70):
            gy = origin_y + top + (y_hi - guide) / (y_hi - y_lo) * plot_h
            parts.append(
                f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="#eeeeee"/>'
            )
            parts.append(
                f'<text x="4" y="{gy + 4:.1f}" font-family="sans-serif" font-size="10" fill="#666">{guide}</text>'
            )
        if len(subset) < 2:
            continue
        for key, color in colors.items():
            coords = []
            for point_index, row in enumerate(subset):
                value = row[key]
                if value is None:
                    continue
                x = left + plot_w * point_index / (len(subset) - 1)
                y = origin_y + top + (y_hi - float(value)) / (y_hi - y_lo) * plot_h
                coords.append(f"{x:.1f},{y:.1f}")
            parts.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="{" ".join(coords)}"/>'
            )
    parts.append(
        '<text x="48" y="'
        + str(len(panels_spec) * height - 8)
        + '" font-family="sans-serif" font-size="11" fill="#1d4e89">v1 1.1.1</text>'
    )
    parts.append(
        '<text x="140" y="'
        + str(len(panels_spec) * height - 8)
        + '" font-family="sans-serif" font-size="11" fill="#b45309">A percentile endpoints</text>'
    )
    body = "".join(parts)
    total_h = len(panels_spec) * height
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" '
        f'viewBox="0 0 {width} {total_h}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>'
        f"{body}</svg>\n"
    )


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    bundle = load_bundle()
    rows, context = build_rows(bundle)
    summary = summarize(rows)
    weekly = weekly_volatility(rows)
    current = current_reading(bundle, context)
    monthly = output_dir / MONTHLY_NAME
    summary_path = output_dir / SUMMARY_NAME
    weekly_path = output_dir / WEEKLY_NAME
    chart_path = output_dir / CHART_NAME
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    _write_csv(monthly, COLUMNS, [csv_fields(row) for row in rows])
    summary_fields = (
        "scenario",
        "scenario_label",
        "window",
        "months",
        "min_index",
        "min_date",
        "max_index",
        "max_date",
        "high",
        "moderate",
        "low",
        "critical",
    )
    rendered_summary = []
    for row in summary:
        rendered = {}
        for column in summary_fields:
            value = row[column]
            if column in ("min_index", "max_index") and value is not None:
                rendered[column] = f"{float(value):.2f}"
            else:
                rendered[column] = "" if value is None else str(value)
        rendered_summary.append(rendered)
    _write_csv(summary_path, summary_fields, rendered_summary)
    weekly_fields = (
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
    rendered_weekly = []
    for row in weekly:
        rendered = {}
        for column in weekly_fields:
            value = row[column]
            if value is None or value == "":
                rendered[column] = ""
            elif column in ("mean_abs_change", "stdev_change", "share_flat", "max_abs_change", "max_drop"):
                rendered[column] = f"{float(value):.4f}"
            else:
                rendered[column] = str(value)
        rendered_weekly.append(rendered)
    _write_csv(weekly_path, weekly_fields, rendered_weekly)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_text(render_svg(rows), encoding="utf-8")
    note.write_text(
        render_markdown(rows, summary, weekly, current, context),
        encoding="utf-8",
    )
    return [monthly, summary_path, weekly_path, chart_path, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.endpoint_calibration",
        description=(
            "Replay methodology 1.1.1 under research endpoints and bands. "
            "Does not publish the weekly score."
        ),
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--note", type=Path, default=PACKAGE_DIR / NOTE_NAME)
    parser.add_argument(
        "--check-locked",
        action="store_true",
        help=f"Print the {PUBLISHED_DATE} six-input score before writing",
    )
    args = parser.parse_args(argv)
    if args.check_locked:
        try:
            scored = score_published_inputs(load_published_raws())
        except (OSError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        band = interpret(scored["index"])["band"]
        print(f"{PUBLISHED_DATE} {scored['index']:.2f} {band} methodology 1.0.0")
        current = current_reading()
        print(
            f"{current['publication_date']} {current['v1_index']:.2f} "
            f"{current['v1_band']} methodology 1.1.1 restatement"
        )
    for path in write_outputs(args.output, args.note):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
