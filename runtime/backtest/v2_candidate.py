# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Research replay of methodology 1.1.1 beside three candidate baskets.

This module does not publish a score. It does not change
``runtime.processing.formula``, the weekly job, ``docs/data/latest.json``,
or the weekly history. Companions stay outside the score.

The v1 column is ``compute_index`` on 1.1.1 inputs: the live endpoints and
weights, crime as the RTCI Nationwide Full Sample rate when that month
exists, and the 1.1.1 homelessness and trust checklist values held constant.
The candidate columns use ``formula.normalize`` and the same
divide-by-sum-of-present-weights rule on a wider basket. They are not a
methodology version.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import mean, stdev
from typing import Mapping, Optional, Sequence

from runtime.backtest.harness import (
    HELD_CONSTANT_BASELINE,
    PUBLISHED_DATE,
    cpi_yoy,
    format_float,
    iter_months,
    prior_year_date,
    score_published_inputs,
    load_published_raws,
)
from runtime.data.fetch.annual_inputs import load_annual_row
from runtime.data.fetch.fetch_incident_rate import PUBLISHED_INCIDENT_RATE
from runtime.processing.formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    compute_index,
    interpret,
    normalize,
)

# This replay's label. Hypothesis h2 was the previous replacement basket.
# Its August 2026 score is cited below and is not recomputed.
HYPOTHESIS_ID = "baskets_a_b_c"
CANDIDATE_LABEL = "v2_baskets_a_b_c"
DATA_PULL_DATE = "2026-09-26"
DEBT_FULL_PULL_DATE = "2026-10-12"
CREDIT_PULL_DATE = "2026-10-12"
VIX_WEEKLY_PULL_DATE = "2026-10-12"
# First month with a CPI year-over-year rate in the BLS fixture, through the
# last headline CPI month in that fixture.
HISTORY_START = "2007-01-01"
HISTORY_END = "2026-08-01"
# BLS cells for this month were non-numeric in the 2026-09-26 pull.
BLS_GAP_MONTH = "2025-10-01"

# Each add-on has the same raw weight. 0.08 is below unemployment (0.12)
# and homelessness (0.09), so an add-on cannot outvote a core input.
# It was not fit to a loss or to the current band.
ADDON_WEIGHT = 0.08
BASKET_ADDONS = {
    "a_labor_food": ("food_cpi_yoy", "prime_age_epop"),
    "b_cost_of_living": ("food_cpi_yoy", "housing_delinquency", "rent_burden_30"),
    "c_financial": ("vix_month_mean", "credit_conditions"),
}
BASKET_ORDER = ("a_labor_food", "b_cost_of_living", "c_financial")
BASKET_TITLE = {
    "a_labor_food": "A labor and food",
    "b_cost_of_living": "B cost of living",
    "c_financial": "C financial stress",
}

# Trial endpoints for series that are not in the live formula.
# v1 endpoints are METRIC_RANGES and are not copied here as a second source.
TRIAL_RANGES = {
    # h2 food range. The older 0–10 draft clamped the 2022 peak.
    "food_cpi_yoy": (-2.0, 15.0),
    # Prime-age EPOP in this fixture runs 69.6 (2020-04) to 80.9.
    # 80.9 is the July 2023 print and is tied through September 2024.
    # 68 to 82 leaves that trough short of a hard floor and that peak short
    # of fully stable. Higher EPOP is more stable.
    "prime_age_epop": (68.0, 82.0),
    # Mortgage delinquency in this fixture runs 1.41 to 11.48.
    "housing_delinquency": (1.0, 12.0),
    # ACS 30%+ rent burden in this fixture runs 48.4 (2019) to 53.4 (2011).
    "rent_burden_30": (40.0, 60.0),
    # Monthly-mean VIX in this fixture runs about 10.13 to 62.67.
    "vix_month_mean": (10.0, 65.0),
    # Chicago Fed NFCI credit subindex. The full file on the 2026-10-12 pull
    # runs about -3.16 to 3.49. -4 to 4 leaves both ends short of a clamp.
    # The subindex is standardized to mean 0 and standard deviation 1.
    "credit_conditions": (-4.0, 4.0),
}
RANGES = dict(METRIC_RANGES)
RANGES.update(TRIAL_RANGES)
INVERSE = frozenset({"trust_in_government", "prime_age_epop"})

# Prior committed h2 replay. Not recomputed. Food −2 to 15, labor blend 72 to
# 82, weights CPI 0.20 / food 0.14 / labor 0.30 / VIX 0.16 / crime 0.20.
# Debt, homelessness, and trust were out of that basket.
H2_PRIOR = {
    "2008-10-01": (50.79, "Low"),
    "2009-10-01": (65.79, "Moderate"),
    "2020-03-01": (62.82, "Moderate"),
    "2020-04-01": (44.34, "Low"),
    "2022-06-01": (59.19, "Moderate"),
    "2026-08-01": (77.28, "High"),
}

KEY_MONTHS = (
    ("2008-10-01", "VIX and credit conditions jump"),
    ("2008-11-01", "VIX monthly-mean peak; credit week of 5 Dec is the file high"),
    ("2009-10-01", "Unemployment 10.0 and mortgage delinquency 10.41"),
    ("2009-12-01", "Great Recession window ends; RTCI crime is still absent"),
    ("2020-03-01", "COVID VIX monthly-mean peak"),
    ("2020-04-01", "Unemployment 14.8 and prime-age EPOP trough; bank delinquency stayed low"),
    ("2022-06-01", "Headline CPI and food CPI high"),
    ("2022-09-01", "Food CPI year-over-year high in this pull"),
    ("2025-10-01", "BLS publication gap"),
    ("2026-04-01", "Last month in the RTCI file"),
    ("2026-08-01", "Last headline CPI month in this pull"),
)

PACKAGE_DIR = Path(__file__).resolve().parent
V2_FIXTURE_DIR = PACKAGE_DIR / "fixtures" / "v2"
OUTPUT_DIR = PACKAGE_DIR / "output"
MONTHLY_NAME = "v2_candidate_monthly.csv"
SUMMARY_NAME = "v2_candidate_summary.csv"
WEEKLY_NAME = "v2_candidate_weekly.csv"
NOTE_NAME = "V2_CANDIDATE.md"
CHART_NAME = "v2_candidate_chart.svg"
ROOT = PACKAGE_DIR.parents[1]
LATEST_PATH = ROOT / "docs" / "data" / "latest.json"

SCORE_NOTE = (
    "Research replay for methodology v2.0 planning. v1_111 is compute_index "
    "on methodology 1.1.1 inputs. Baskets A, B, and C keep those inputs and "
    "add series at weight 0.08 each. They are not a contract and they are "
    "not the published BugOut Index."
)

SUMMARY_SCENARIOS = (
    ("v1_111", "methodology 1.1.1 (Nationwide Full Sample crime; homelessness 0.22 and trust 39 held)"),
    ("v1_partial", "inflation, unemployment, and debt only"),
    ("v1_100_held", "1.0.0 pins on the same FRED inputs (crime 2723, homelessness 0.23, trust 41)"),
    ("a_labor_food", "A: 1.1.1 plus prime-age EPOP and food CPI"),
    ("b_cost_of_living", "B: 1.1.1 plus food CPI, mortgage delinquency, and rent burden"),
    ("c_financial", "C: 1.1.1 plus VIX and the Chicago Fed credit subindex"),
)
SUMMARY_WINDOWS = ("all", "2008", "2020", "2022")


def food_public_yoy(current: object, previous: object) -> Optional[float]:
    """12-month food percent change, half-up to one decimal.

    Same public print as ``fetch_food_shadow._public_yoy``.
    """
    try:
        cur = Decimal(str(current).strip())
        prev = Decimal(str(previous).strip())
    except Exception:
        return None
    if prev == 0:
        return None
    pct = ((cur - prev) / prev) * Decimal(100)
    return float(pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _load_text_series(path: Path) -> dict[str, str]:
    points: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if len(fields) < 2:
            raise ValueError(f"{path} needs a date column and a value column")
        for row in reader:
            day = (row.get(fields[0]) or "").strip()
            raw = (row.get(fields[1]) or "").strip()
            if day and raw:
                points[day] = raw
    if not points:
        raise ValueError(f"{path} has no observations")
    return points


def _as_float_map(texts: Mapping[str, str]) -> dict[str, float]:
    return {day: float(raw) for day, raw in texts.items()}


def _load_rent_burden(path: Path) -> tuple[dict[str, float], dict[str, float]]:
    thirty: dict[str, float] = {}
    fifty: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = (row.get("observation_date") or "").strip()
            if not day:
                continue
            thirty[day] = float(row["rent_burden_30_plus"])
            fifty[day] = float(row["rent_burden_50_plus"])
    if not thirty:
        raise ValueError(f"{path} has no observations")
    return thirty, fifty


def load_v2_bundle(directory: Optional[Path] = None) -> dict:
    """Offline fixtures. No network and no FRED key."""
    folder = V2_FIXTURE_DIR if directory is None else directory
    vix_rows = {}
    with (folder / "VIXCLS_monthly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            vix_rows[row["observation_date"]] = {
                "mean": float(row["vix_month_mean"]),
                "max": float(row["vix_month_max"]),
                "observations": int(row["observations"]),
            }
    vix_weekly = {}
    with (folder / "VIXCLS_weekly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            vix_weekly[row["week_ending"]] = {
                "mean": float(row["vix_week_mean"]),
                "observations": int(row["observations"]),
            }
    crime = {}
    with (folder / "RTCI_monthly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            crime[row["observation_date"]] = {
                "unweighted": float(row["incident_rate_unweighted"]),
                "population_weighted": float(row["incident_rate_population_weighted"]),
                "agencies": int(row["agencies"]),
            }
    rent_30, rent_50 = _load_rent_burden(folder / "B25070.csv")
    credit = _as_float_map(_load_text_series(folder / "NFCICREDIT_weekly.csv"))
    return {
        "cpi": _load_text_series(folder / "CPIAUCSL.csv"),
        "food": _load_text_series(folder / "CPIUFDNS.csv"),
        "epop": _as_float_map(_load_text_series(folder / "LNS12300060.csv")),
        "unrate": _as_float_map(_load_text_series(folder / "LNS14000000.csv")),
        "vix": vix_rows,
        "vix_weekly": vix_weekly,
        "crime": crime,
        "debt": _as_float_map(_load_text_series(folder / "GFDEGDQ188S_full.csv")),
        "housing_delinquency": _as_float_map(_load_text_series(folder / "DRSFRMACBS.csv")),
        "rent_burden_30": rent_30,
        "rent_burden_50": rent_50,
        "credit": credit,
    }


def asof(series: Mapping[str, float], day: str) -> tuple[Optional[float], str, str]:
    """Latest print on or before ``day``.

    The print's own date is ``observed``. A later date keeps that print as
    ``carried_forward``. A date before the first print is ``excluded``.
    This is not an interpolation.
    """
    available = [stamp for stamp in series if stamp <= day]
    if not available:
        return None, "excluded", ""
    chosen = max(available)
    status = "observed" if chosen == day else "carried_forward"
    return series[chosen], status, chosen


def _inflation_from_texts(levels: Mapping[str, str], day: str) -> Optional[float]:
    prior = prior_year_date(day)
    current = levels.get(day)
    previous = levels.get(prior)
    if current is None or previous is None:
        return None
    try:
        current_f = float(current)
        previous_f = float(previous)
    except ValueError:
        return None
    if previous_f == 0:
        return None
    return cpi_yoy(current_f, previous_f)


def _food_from_texts(levels: Mapping[str, str], day: str) -> Optional[float]:
    prior = prior_year_date(day)
    if day not in levels or prior not in levels:
        return None
    return food_public_yoy(levels[day], levels[prior])


def _crime_for(day: str, crime: Mapping[str, dict]) -> tuple:
    """Nationwide Full Sample rate for ``day``.

    A month inside the file is ``observed``. Months after the file's last
    month carry that last rate, which is how methodology 1.1.1 publishes
    the latest file month. Months before the file starts are ``excluded``.
    The carried value is not a later month's crime observation.
    """
    if day in crime:
        row = crime[day]
        return (
            row["population_weighted"],
            "observed",
            day,
            row["agencies"],
            row["unweighted"],
        )
    last = max(crime)
    if day > last:
        row = crime[last]
        return (
            row["population_weighted"],
            "carried_forward",
            last,
            row["agencies"],
            row["unweighted"],
        )
    return None, "excluded", "", None, None


def _credit_month_mean(credit: Mapping[str, float], day: str) -> Optional[float]:
    prefix = day[:7]
    weeks = [value for stamp, value in credit.items() if stamp[:7] == prefix]
    if not weeks:
        return None
    return mean(weeks)


def checklist_pins() -> dict[str, float]:
    """Methodology 1.1.1 annual cells. Held on every historical month."""
    homelessness = load_annual_row("homelessness_rate")
    trust = load_annual_row("trust_in_government")
    return {
        "homelessness_rate": float(homelessness["value"]),
        "trust_in_government": float(trust["value"]),
        "homelessness_observation_date": str(homelessness["observation_date"]),
        "trust_observation_date": str(trust["observation_date"]),
    }


def basket_weights(basket: str) -> dict[str, float]:
    weights = {name: WEIGHTS[name] for name in CORE_METRICS}
    for name in BASKET_ADDONS[basket]:
        weights[name] = ADDON_WEIGHT
    return weights


def score_weighted(values: Mapping[str, Optional[float]], weights: Mapping[str, float]) -> dict:
    """Normalize, then divide by the sum of weights that were present.

    A missing input shrinks the denominator. It is not treated as zero
    stress. An empty basket returns a null index.
    """
    total_weighted = 0.0
    total_weight = 0.0
    present = []
    excluded = []
    norms: dict[str, Optional[float]] = {}
    for name, weight in weights.items():
        raw = values.get(name)
        if raw is None or not isinstance(raw, (int, float)):
            excluded.append(name)
            norms[name] = None
            continue
        lo, hi = RANGES[name]
        norm = normalize(float(raw), lo, hi, inverse=name in INVERSE)
        norms[name] = norm
        total_weighted += norm * weight
        total_weight += weight
        present.append(name)
    if total_weight == 0:
        index = None
        band = ""
    else:
        index = round(total_weighted / total_weight, 2)
        band = interpret(index)["band"]
    return {
        "index": index,
        "band": band,
        "denominator": total_weight,
        "present": present,
        "excluded": excluded,
        "norms": norms,
    }


def _v1_index(raws: Mapping[str, Optional[float]]) -> tuple[Optional[float], str]:
    payload = {}
    for metric, value in raws.items():
        if value is None or not isinstance(value, (int, float)):
            continue
        if metric not in WEIGHTS:
            continue
        payload[metric] = {"data": {metric: float(value)}}
    if not payload:
        return None, ""
    scored = compute_index(payload)
    return scored["index"], interpret(scored["index"])["band"]


def assign_window(day: str) -> str:
    if "2007-12-01" <= day <= "2009-12-01":
        return "2008"
    if day.startswith("2020-"):
        return "2020"
    if day.startswith("2022-"):
        return "2022"
    return "history"


def month_values(day: str, bundle: Mapping, pins: Mapping[str, float]) -> dict:
    """Inputs for one calendar month. Annual 1.1.1 pins are held, labeled later."""
    inflation = _inflation_from_texts(bundle["cpi"], day)
    food = _food_from_texts(bundle["food"], day)
    debt, debt_status, debt_date = asof(bundle["debt"], day)
    housing, housing_status, housing_date = asof(bundle["housing_delinquency"], day)
    rent, rent_status, rent_date = asof(bundle["rent_burden_30"], day)
    rent50 = None if not rent_date else bundle["rent_burden_50"].get(rent_date)
    crime, crime_status, crime_date, agencies, unweighted = _crime_for(day, bundle["crime"])
    vix = bundle["vix"].get(day)
    return {
        "inflation_rate": inflation,
        "unemployment_rate": bundle["unrate"].get(day),
        "debt_to_gdp_ratio": debt,
        "debt_status": debt_status,
        "debt_observation_date": debt_date,
        "incident_rate": crime,
        "incident_unweighted": unweighted,
        "incident_status": crime_status,
        "incident_observation_date": crime_date,
        "incident_agencies": agencies,
        "homelessness_rate": float(pins["homelessness_rate"]),
        "trust_in_government": float(pins["trust_in_government"]),
        "food_cpi_yoy": food,
        "prime_age_epop": bundle["epop"].get(day),
        "housing_delinquency": housing,
        "housing_status": housing_status,
        "housing_observation_date": housing_date,
        "rent_burden_30": rent,
        "rent_burden_50": rent50,
        "rent_status": rent_status,
        "rent_observation_date": rent_date,
        "vix_month_mean": None if vix is None else vix["mean"],
        "credit_conditions": _credit_month_mean(bundle["credit"], day),
    }


def _score_row(values: Mapping) -> dict:
    v1_raws = {metric: values.get(metric) for metric in CORE_METRICS}
    v1_index, v1_band = _v1_index(v1_raws)
    v1_scored = score_weighted(values, {name: WEIGHTS[name] for name in CORE_METRICS})
    partial_raws = {
        "inflation_rate": values.get("inflation_rate"),
        "unemployment_rate": values.get("unemployment_rate"),
        "debt_to_gdp_ratio": values.get("debt_to_gdp_ratio"),
    }
    partial_index, partial_band = _v1_index(partial_raws)
    held_raws = {
        "inflation_rate": values.get("inflation_rate"),
        "unemployment_rate": values.get("unemployment_rate"),
        "debt_to_gdp_ratio": values.get("debt_to_gdp_ratio"),
        "incident_rate": float(HELD_CONSTANT_BASELINE["incident_rate"]),
        "homelessness_rate": float(HELD_CONSTANT_BASELINE["homelessness_rate"]),
        "trust_in_government": float(HELD_CONSTANT_BASELINE["trust_in_government"]),
    }
    held_index, held_band = _v1_index(held_raws)
    baskets = {
        name: score_weighted(values, basket_weights(name)) for name in BASKET_ORDER
    }
    return {
        "v1": {"index": v1_index, "band": v1_band, "detail": v1_scored},
        "partial": {"index": partial_index, "band": partial_band},
        "held_100": {"index": held_index, "band": held_band},
        "baskets": baskets,
    }


def build_v2_rows(bundle: Optional[Mapping] = None) -> list[dict]:
    """One row per month from January 2007 through August 2026."""
    bundle = load_v2_bundle() if bundle is None else bundle
    pins = checklist_pins()
    rows = []
    for day in iter_months(HISTORY_START, HISTORY_END):
        values = month_values(day, bundle, pins)
        scored = _score_row(values)
        v1 = scored["v1"]
        detail = v1["detail"]
        basket_a = scored["baskets"]["a_labor_food"]
        basket_b = scored["baskets"]["b_cost_of_living"]
        basket_c = scored["baskets"]["c_financial"]
        rows.append(
            {
                "date": day,
                "window": assign_window(day),
                "candidate_label": CANDIDATE_LABEL,
                "methodology_reference": "1.1.1",
                "inflation_rate": values["inflation_rate"],
                "unemployment_rate": values["unemployment_rate"],
                "debt_to_gdp_ratio": values["debt_to_gdp_ratio"],
                "debt_status": values["debt_status"],
                "debt_observation_date": values["debt_observation_date"],
                "incident_rate": values["incident_rate"],
                "incident_unweighted": values["incident_unweighted"],
                "incident_status": values["incident_status"],
                "incident_observation_date": values["incident_observation_date"],
                "incident_agencies": values["incident_agencies"],
                "homelessness_rate": values["homelessness_rate"],
                "trust_in_government": values["trust_in_government"],
                "food_cpi_yoy": values["food_cpi_yoy"],
                "prime_age_epop": values["prime_age_epop"],
                "housing_delinquency": values["housing_delinquency"],
                "housing_status": values["housing_status"],
                "housing_observation_date": values["housing_observation_date"],
                "rent_burden_30": values["rent_burden_30"],
                "rent_burden_50": values["rent_burden_50"],
                "rent_status": values["rent_status"],
                "rent_observation_date": values["rent_observation_date"],
                "vix_month_mean": values["vix_month_mean"],
                "credit_conditions": values["credit_conditions"],
                "food_normalized": _round_norm(basket_a["norms"].get("food_cpi_yoy")),
                "epop_normalized": _round_norm(basket_a["norms"].get("prime_age_epop")),
                "housing_normalized": _round_norm(basket_b["norms"].get("housing_delinquency")),
                "rent_normalized": _round_norm(basket_b["norms"].get("rent_burden_30")),
                "vix_normalized": _round_norm(basket_c["norms"].get("vix_month_mean")),
                "credit_normalized": _round_norm(basket_c["norms"].get("credit_conditions")),
                "v1_111_index": v1["index"],
                "v1_111_band": v1["band"],
                "v1_111_denominator": detail["denominator"],
                "v1_111_inputs_present": "|".join(detail["present"]),
                "v1_111_inputs_excluded": "|".join(detail["excluded"]),
                "v1_partial_index": scored["partial"]["index"],
                "v1_partial_band": scored["partial"]["band"],
                "v1_100_held_index": scored["held_100"]["index"],
                "v1_100_held_band": scored["held_100"]["band"],
                "a_index": basket_a["index"],
                "a_band": basket_a["band"],
                "a_denominator": basket_a["denominator"],
                "b_index": basket_b["index"],
                "b_band": basket_b["band"],
                "b_denominator": basket_b["denominator"],
                "c_index": basket_c["index"],
                "c_band": basket_c["band"],
                "c_denominator": basket_c["denominator"],
                "score_note": SCORE_NOTE,
            }
        )
    return rows


def _round_norm(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def current_reading(bundle: Optional[Mapping] = None) -> dict:
    """1.1.1 restatement of the committed latest.json inputs, plus add-ons.

    The six published raws are scored as methodology 1.1.0 stored them.
    The restatement replaces only homelessness and trust with the 1.1.1
    checklist. Add-ons use the latest shadow or fixture print on or before
    the publication date. This does not write ``latest.json``.
    """
    bundle = load_v2_bundle() if bundle is None else bundle
    latest = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    pins = checklist_pins()
    published = {metric: float(latest["metrics"][metric]["raw"]) for metric in CORE_METRICS}
    published_index, published_band = _v1_index(published)
    restated = dict(published)
    restated["homelessness_rate"] = float(pins["homelessness_rate"])
    restated["trust_in_government"] = float(pins["trust_in_government"])
    publication = str(latest["publication_date"])
    food = latest["food_shadow"]["values"]["food_cpi_yoy"]
    food_date = latest["food_shadow"]["dates"]["food_cpi_yoy"]
    epop = latest["labor_shadow"]["values"]["prime_age_epop"]
    epop_date = latest["labor_shadow"]["dates"]["prime_age_epop"]
    housing, housing_status, housing_date = asof(bundle["housing_delinquency"], publication)
    rent, rent_status, rent_date = asof(bundle["rent_burden_30"], publication)
    credit_stamp = max(stamp for stamp in bundle["credit"] if stamp <= publication)
    vix_stamp = max(stamp for stamp in bundle["vix_weekly"] if stamp <= publication)
    values = {
        "inflation_rate": restated["inflation_rate"],
        "unemployment_rate": restated["unemployment_rate"],
        "debt_to_gdp_ratio": restated["debt_to_gdp_ratio"],
        "incident_rate": restated["incident_rate"],
        "homelessness_rate": restated["homelessness_rate"],
        "trust_in_government": restated["trust_in_government"],
        "food_cpi_yoy": float(food),
        "prime_age_epop": float(epop),
        "housing_delinquency": housing,
        "rent_burden_30": rent,
        "vix_month_mean": bundle["vix_weekly"][vix_stamp]["mean"],
        "credit_conditions": bundle["credit"][credit_stamp],
    }
    scored = _score_row(values)
    return {
        "publication_date": publication,
        "published_methodology": latest["methodology_version"],
        "published_index": published_index,
        "published_band": published_band,
        "published_file_index": latest["bugout_index"],
        "values": values,
        "food_date": food_date,
        "epop_date": epop_date,
        "housing_status": housing_status,
        "housing_date": housing_date,
        "rent_status": rent_status,
        "rent_date": rent_date,
        "vix_week": vix_stamp,
        "credit_week": credit_stamp,
        "pins": pins,
        "scored": scored,
        "unemployment_date": latest["metrics"]["unemployment_rate"]["observation_date"],
        "inflation_date": latest["metrics"]["inflation_rate"]["observation_date"],
        "incident_date": latest["metrics"]["incident_rate"]["observation_date"],
        "debt_date": latest["metrics"]["debt_to_gdp_ratio"]["observation_date"],
    }


COLUMNS = (
    "date",
    "window",
    "candidate_label",
    "methodology_reference",
    "inflation_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "debt_status",
    "debt_observation_date",
    "incident_rate",
    "incident_unweighted",
    "incident_status",
    "incident_observation_date",
    "incident_agencies",
    "homelessness_rate",
    "trust_in_government",
    "food_cpi_yoy",
    "prime_age_epop",
    "housing_delinquency",
    "housing_status",
    "housing_observation_date",
    "rent_burden_30",
    "rent_burden_50",
    "rent_status",
    "rent_observation_date",
    "vix_month_mean",
    "credit_conditions",
    "food_normalized",
    "epop_normalized",
    "housing_normalized",
    "rent_normalized",
    "vix_normalized",
    "credit_normalized",
    "v1_111_index",
    "v1_111_band",
    "v1_111_denominator",
    "v1_111_inputs_present",
    "v1_111_inputs_excluded",
    "v1_partial_index",
    "v1_partial_band",
    "v1_100_held_index",
    "v1_100_held_band",
    "a_index",
    "a_band",
    "a_denominator",
    "b_index",
    "b_band",
    "b_denominator",
    "c_index",
    "c_band",
    "c_denominator",
    "score_note",
)

_INDEX_COLUMNS = {
    "food_normalized",
    "epop_normalized",
    "housing_normalized",
    "rent_normalized",
    "vix_normalized",
    "credit_normalized",
    "v1_111_index",
    "v1_111_denominator",
    "v1_partial_index",
    "v1_100_held_index",
    "a_index",
    "a_denominator",
    "b_index",
    "b_denominator",
    "c_index",
    "c_denominator",
}


def csv_fields(row: Mapping[str, object]) -> dict[str, str]:
    rendered = {}
    for column in COLUMNS:
        value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in _INDEX_COLUMNS:
            rendered[column] = f"{float(value):.2f}"
        elif isinstance(value, float):
            rendered[column] = format_float(value)
        else:
            rendered[column] = str(value)
    return rendered


def write_monthly(rows: Sequence[Mapping[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(csv_fields(row))


def _extremes(values: Sequence[tuple[str, Optional[float]]]) -> Optional[dict]:
    usable = [(day, value) for day, value in values if value is not None]
    if not usable:
        return None
    min_day, min_value = min(usable, key=lambda item: (item[1], item[0]))
    max_day, max_value = max(usable, key=lambda item: (item[1], item[0]))
    return {
        "min": min_value,
        "min_date": min_day,
        "max": max_value,
        "max_date": max_day,
        "n": len(usable),
    }


def _band_counts(bands: Sequence[str]) -> dict[str, int]:
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


_SUMMARY_INDEX = {
    "v1_111": "v1_111_index",
    "v1_partial": "v1_partial_index",
    "v1_100_held": "v1_100_held_index",
    "a_labor_food": "a_index",
    "b_cost_of_living": "b_index",
    "c_financial": "c_index",
}


def summarize(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    """One summary row per scenario and window. ``all`` is the full file."""
    summary = []
    for scenario, label in SUMMARY_SCENARIOS:
        index_column = _SUMMARY_INDEX[scenario]
        band_column = index_column.replace("_index", "_band")
        for window_name in SUMMARY_WINDOWS:
            if window_name == "all":
                subset = list(rows)
            else:
                subset = [row for row in rows if row["window"] == window_name]
            ends = _extremes([(str(row["date"]), row[index_column]) for row in subset])
            counts = _band_counts(
                [
                    str(row[band_column])
                    for row in subset
                    if row[index_column] is not None
                ]
            )
            summary.append(
                {
                    "scenario": scenario,
                    "scenario_label": label,
                    "window": window_name,
                    "months_scored": 0 if ends is None else ends["n"],
                    "min_index": None if ends is None else ends["min"],
                    "min_date": "" if ends is None else ends["min_date"],
                    "max_index": None if ends is None else ends["max"],
                    "max_date": "" if ends is None else ends["max_date"],
                    "high": counts["High Stability"],
                    "moderate": counts["Moderate Stability"],
                    "low": counts["Low Stability"],
                    "critical": counts["Critical Instability"],
                }
            )
    return summary


SUMMARY_COLUMNS = (
    "scenario",
    "scenario_label",
    "window",
    "months_scored",
    "min_index",
    "min_date",
    "max_index",
    "max_date",
    "high",
    "moderate",
    "low",
    "critical",
)


def write_summary(summary: Sequence[Mapping[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SUMMARY_COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in summary:
            rendered = {}
            for column in SUMMARY_COLUMNS:
                value = row[column]
                if value is None or value == "":
                    rendered[column] = ""
                elif column in ("min_index", "max_index"):
                    rendered[column] = f"{float(value):.2f}"
                else:
                    rendered[column] = str(value)
            writer.writerow(rendered)


def _friday_month(friday: str) -> str:
    return friday[:7] + "-01"


def weekly_volatility(bundle: Optional[Mapping] = None) -> list[dict]:
    """Friday-to-Friday changes.

    Within a month, baskets A and B and methodology 1.1.1 are constant,
    because their inputs are monthly or slower. Basket C moves when that
    week's VIX mean or that Friday's credit subindex moves. ``all_fridays``
    also includes the step from the last Friday of one month to the first
    Friday of the next, which is where a new monthly print shows up.
    """
    bundle = load_v2_bundle() if bundle is None else bundle
    pins = checklist_pins()
    month_cache = {
        day: month_values(day, bundle, pins)
        for day in iter_months(HISTORY_START, HISTORY_END)
    }
    fridays = [
        stamp
        for stamp in sorted(bundle["vix_weekly"])
        if stamp in bundle["credit"] and HISTORY_START <= _friday_month(stamp) <= HISTORY_END
    ]
    series: dict[str, list[tuple[str, str, float]]] = {
        "v1_111": [],
        "a_labor_food": [],
        "b_cost_of_living": [],
        "c_financial": [],
    }
    for friday in fridays:
        month = _friday_month(friday)
        values = dict(month_cache[month])
        values["vix_month_mean"] = bundle["vix_weekly"][friday]["mean"]
        values["credit_conditions"] = bundle["credit"][friday]
        scored = _score_row(values)
        points = {
            "v1_111": scored["v1"]["index"],
            "a_labor_food": scored["baskets"]["a_labor_food"]["index"],
            "b_cost_of_living": scored["baskets"]["b_cost_of_living"]["index"],
            "c_financial": scored["baskets"]["c_financial"]["index"],
        }
        for name, index in points.items():
            if index is not None:
                series[name].append((friday, month, float(index)))

    samples = {
        "within_month": lambda prev, cur: prev[1] == cur[1],
        "within_month_2008": lambda prev, cur: prev[1] == cur[1] and assign_window(cur[1]) == "2008",
        "within_month_2020": lambda prev, cur: prev[1] == cur[1] and assign_window(cur[1]) == "2020",
        "within_month_2022": lambda prev, cur: prev[1] == cur[1] and assign_window(cur[1]) == "2022",
        "all_fridays": lambda prev, cur: True,
    }
    rows = []
    for basket, points in series.items():
        for sample, predicate in samples.items():
            deltas = []
            for prev, cur in zip(points, points[1:]):
                if predicate(prev, cur):
                    deltas.append((cur[0], round(cur[2] - prev[2], 2)))
            rows.append(_delta_summary(basket, sample, deltas))
    return rows


def _delta_summary(basket: str, sample: str, deltas: list[tuple[str, float]]) -> dict:
    if not deltas:
        return {
            "basket": basket,
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
    abs_changes = [abs(change) for change in changes]
    max_abs_week, max_abs = max(deltas, key=lambda item: (abs(item[1]), item[0]))
    drop_week, drop = min(deltas, key=lambda item: (item[1], item[0]))
    flat = sum(1 for change in changes if change == 0.0)
    deviation = stdev(changes) if len(changes) > 1 else 0.0
    return {
        "basket": basket,
        "sample": sample,
        "weeks": len(deltas),
        "mean_abs_change": mean(abs_changes),
        "stdev_change": deviation,
        "share_flat": flat / len(changes),
        "max_abs_change": abs(max_abs),
        "max_abs_week": max_abs_week,
        "max_drop": drop,
        "max_drop_week": drop_week,
    }


WEEKLY_COLUMNS = (
    "basket",
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


def write_weekly(rows: Sequence[Mapping[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(WEEKLY_COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            rendered = {}
            for column in WEEKLY_COLUMNS:
                value = row[column]
                if value is None or value == "":
                    rendered[column] = ""
                elif column in ("mean_abs_change", "stdev_change", "max_abs_change", "max_drop"):
                    rendered[column] = f"{float(value):.4f}"
                elif column == "share_flat":
                    rendered[column] = f"{float(value):.4f}"
                else:
                    rendered[column] = str(value)
            writer.writerow(rendered)


def _short_band(band: object) -> str:
    text = str(band or "")
    if not text:
        return "—"
    return text.replace(" Stability", "").replace(" Instability", "")


def _num(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.{digits}f}"


def _signed(value: float) -> str:
    number = float(value)
    if number.is_integer():
        text = str(int(number))
    else:
        text = f"{number:g}"
    if number < 0:
        return "−" + text[1:]
    return text


def _by_date(rows: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    return {str(row["date"]): row for row in rows}


def _cell(row: Mapping[str, object], index_key: str) -> str:
    band_key = index_key.replace("_index", "_band")
    if row.get(index_key) is None:
        return "—"
    return f"{_num(row[index_key])} {_short_band(row.get(band_key))}"


def _summary_lookup(summary: Sequence[Mapping], scenario: str, window: str) -> Mapping:
    for row in summary:
        if row["scenario"] == scenario and row["window"] == window:
            return row
    raise KeyError((scenario, window))


def _range_phrase(summary_row: Mapping) -> str:
    return (
        f"{_num(summary_row['min_index'])} ({summary_row['min_date']}) to "
        f"{_num(summary_row['max_index'])} ({summary_row['max_date']})"
    )


def _weekly_lookup(weekly: Sequence[Mapping], basket: str, sample: str) -> Mapping:
    for row in weekly:
        if row["basket"] == basket and row["sample"] == sample:
            return row
    raise KeyError((basket, sample))


def _direction(component: Optional[float], index: Optional[float]) -> str:
    if component is None or index is None:
        return "is missing, so its weight drops out"
    if component > index + 0.05:
        return f"normalizes to {_num(component)}, above the 1.1.1 reading, so it pulls the basket up"
    if component < index - 0.05:
        return f"normalizes to {_num(component)}, below the 1.1.1 reading, so it pulls the basket down"
    return f"normalizes to {_num(component)}, close to the 1.1.1 reading"


def render_markdown(
    rows: Sequence[Mapping[str, object]],
    summary: Sequence[Mapping[str, object]],
    weekly: Sequence[Mapping[str, object]],
    current: Mapping[str, object],
    bundle: Optional[Mapping] = None,
) -> str:
    """Results note. Numbers come from the rows just scored."""
    bundle = load_v2_bundle() if bundle is None else bundle
    by_date = _by_date(rows)
    scored = current["scored"]
    values = current["values"]
    pins = current["pins"]

    def current_cell(basket_key: str) -> str:
        if basket_key == "v1":
            index = scored["v1"]["index"]
            band = scored["v1"]["band"]
        else:
            index = scored["baskets"][basket_key]["index"]
            band = scored["baskets"][basket_key]["band"]
        return f"{_num(index)} {_short_band(band)}"

    comparison = [
        "| Reading | v1 1.1.1 | A labor and food | B cost of living | C financial stress |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| Current ({current['publication_date']} inputs, 1.1.1 checklist) | "
            f"{current_cell('v1')} | {current_cell('a_labor_food')} | "
            f"{current_cell('b_cost_of_living')} | {current_cell('c_financial')} |"
        ),
    ]
    for day, reason in KEY_MONTHS:
        row = by_date[day]
        comparison.append(
            "| {day} — {reason} | {v1} | {a} | {b} | {c} |".format(
                day=day,
                reason=reason,
                v1=_cell(row, "v1_111_index"),
                a=_cell(row, "a_index"),
                b=_cell(row, "b_index"),
                c=_cell(row, "c_index"),
            )
        )

    window_titles = (
        ("all", "Full history (Jan 2007–Aug 2026)"),
        ("2008", "2008 (Dec 2007–Dec 2009)"),
        ("2020", "2020 (Jan–Dec)"),
        ("2022", "2022 inflation year"),
    )
    range_lines = [
        "| Window | v1 1.1.1 | A labor and food | B cost of living | C financial stress |",
        "| --- | --- | --- | --- | --- |",
    ]
    band_lines = [
        "| Window | Basket | High | Moderate | Low | Critical |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for window_name, title in window_titles:
        range_lines.append(
            "| {title} | {v1} | {a} | {b} | {c} |".format(
                title=title,
                v1=_range_phrase(_summary_lookup(summary, "v1_111", window_name)),
                a=_range_phrase(_summary_lookup(summary, "a_labor_food", window_name)),
                b=_range_phrase(_summary_lookup(summary, "b_cost_of_living", window_name)),
                c=_range_phrase(_summary_lookup(summary, "c_financial", window_name)),
            )
        )
        for scenario, title_s in (
            ("v1_111", "v1 1.1.1"),
            ("a_labor_food", "A"),
            ("b_cost_of_living", "B"),
            ("c_financial", "C"),
        ):
            item = _summary_lookup(summary, scenario, window_name)
            band_lines.append(
                f"| {title} | {title_s} | {item['high']} | {item['moderate']} | "
                f"{item['low']} | {item['critical']} |"
            )

    h2_lines = [
        "| Month | Prior h2 |",
        "| --- | --- |",
    ]
    for day, (index, band) in H2_PRIOR.items():
        h2_lines.append(f"| {day} | {index:.2f} {band} |")

    weight_rows = [
        ("Headline CPI YoY (`CPIAUCSL`)", "0.15", "−10 to 15", "higher is less stable", "Live inflation input. In every basket."),
        ("Crime, RTCI Nationwide Full Sample", "0.12", "500 to 8,000", "higher is less stable", "Live crime input from methodology 1.1.0. Absent before January 2018. Carried after the file's last month."),
        ("Unemployment (`UNRATE`)", "0.12", "0 to 25", "higher is less stable", "Live labor input. Basket A adds EPOP beside it and does not replace it."),
        ("Debt-to-GDP (`GFDEGDQ188S`)", "0.12", "0 to 200", "higher is less stable", "Live input. This replay uses the quarterly file through 2026 Q1."),
        ("Homelessness", "0.09", "0 to 0.5", "higher is less stable", f"Held at the 1.1.1 checklist {_num(pins['homelessness_rate'], 2)} ({pins['homelessness_observation_date']}). Not a historical path."),
        ("Trust in government", "0.12", "0 to 80", "higher is more stable", f"Held at the 1.1.1 checklist {_num(pins['trust_in_government'], 0)} (survey year {pins['trust_observation_date']}). Not a historical path."),
        ("Food CPI YoY (`CPIUFDNS`)", "0.08", "−2 to 15", "higher is less stable", "Baskets A and B. Same one-decimal print as the food shadow. The live score does not use it."),
        ("Prime-age EPOP (`LNS12300060`)", "0.08", "68 to 82", "higher is more stable", "Basket A only. Not the 0.70/0.30 labor blend."),
        ("Mortgage delinquency (`DRSFRMACBS`)", "0.08", "1 to 12", "higher is less stable", "Basket B. Quarterly bank series, carried forward within the file."),
        ("Rent burden, ACS 30%+ (`B25070`)", "0.08", "40 to 60", "higher is less stable", "Basket B. Annual. The 50%+ share is stored and not scored."),
        ("VIX monthly mean (`VIXCLS`)", "0.08", "10 to 65", "higher is less stable", "Basket C. Mean of daily closes. The weekly path uses that week's mean in the same slot."),
        ("Credit conditions (`NFCICREDIT`)", "0.08", "−4 to 4", "higher is less stable", "Basket C. Chicago Fed NFCI credit subindex, monthly mean of the Friday prints. Not an ICE or Moody's spread."),
    ]
    weight_lines = [
        "| Input | Raw weight | Range | Direction | Where it sits |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, weight, span, direction, where in weight_rows:
        weight_lines.append(f"| {label} | {weight} | {span} | {direction} | {where} |")

    credit_values = bundle["credit"]
    credit_low = min(credit_values, key=lambda stamp: (credit_values[stamp], stamp))
    credit_high = max(credit_values, key=lambda stamp: (credit_values[stamp], stamp))
    epop_values = bundle["epop"]
    epop_low = min(epop_values, key=lambda stamp: (epop_values[stamp], stamp))
    epop_high = max(epop_values, key=lambda stamp: (epop_values[stamp], stamp))

    weekly_lines = [
        "| Basket | Sample | Weeks | Mean abs move | Stdev of move | Share flat | Largest move | Largest drop |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for basket, label in (
        ("v1_111", "v1 1.1.1"),
        ("a_labor_food", "A"),
        ("b_cost_of_living", "B"),
        ("c_financial", "C"),
    ):
        for sample in ("within_month", "all_fridays", "within_month_2008", "within_month_2020", "within_month_2022"):
            item = _weekly_lookup(weekly, basket, sample)
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

    v1_within = _weekly_lookup(weekly, "v1_111", "within_month")
    c_within = _weekly_lookup(weekly, "c_financial", "within_month")
    c_2008 = _weekly_lookup(weekly, "c_financial", "within_month_2008")
    v1_all = _weekly_lookup(weekly, "v1_111", "all_fridays")

    aug = by_date["2026-08-01"]
    oct_2008 = by_date["2008-10-01"]
    oct_2009 = by_date["2009-10-01"]
    apr_2020 = by_date["2020-04-01"]
    jun_2022 = by_date["2022-06-01"]
    oct_2025 = by_date["2025-10-01"]
    apr_2026 = by_date["2026-04-01"]
    dec_2009 = by_date["2009-12-01"]
    sep_2011 = by_date["2011-09-01"]

    y2022 = [row for row in rows if row["window"] == "2022"]
    y2022_v1_low = sum(1 for row in y2022 if row["v1_111_band"] == "Low Stability")

    a_norms = scored["baskets"]["a_labor_food"]["norms"]
    b_norms = scored["baskets"]["b_cost_of_living"]["norms"]
    c_norms = scored["baskets"]["c_financial"]["norms"]
    v1_now = scored["v1"]["index"]

    text = f"""# v2 candidate replay (baskets A, B, and C)

Research only. This note is not a methodology version, and it is not the live BugOut Index. The scores below are not inputs to `compute_index`, the weekly publisher, `docs/data/latest.json`, or the weekly history. Pew trust, Gallup confidence, and the shelter companions stay outside the score. Merging this branch does not publish to GitHub Pages.

**Stay on methodology 1.1.1.** The current reading is **{_num(v1_now)} {_short_band(scored['v1']['band'])}**. Basket A is **{current_cell('a_labor_food')}**, basket B is **{current_cell('b_cost_of_living')}**, and basket C is **{current_cell('c_financial')}**. All four sit in Moderate. The previous hypothesis h2 printed **77.28 High** for August 2026. That basket dropped debt, homelessness, and trust and filled the weight with a calm labor blend and a calm VIX. The High reading was that composition. These three baskets keep the six 1.1.1 inputs. Each add-on that is calm today lifts the reading, and each basket that catches one stress period is calm through another. Headline CPI already puts every month of 2022 in Low Stability on 1.1.1 ({y2022_v1_low} of {len(y2022)} months). A new published basket is not required to see that year.

Read this file. You do not need to run the harness. Month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). Friday-to-Friday moves are in [`output/v2_candidate_weekly.csv`](output/v2_candidate_weekly.csv). A chart of the same monthly series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

The 19 September 2026 published row still scores **57.11 Moderate** through `compute_index` under methodology 1.0.0 (crime 2723, homelessness 0.23, trust 41). The committed `latest.json` is the 9 October 2026 week, methodology 1.1.0, index **{_num(current['published_file_index'])}**. Scoring those six published raws through `compute_index` returns **{_num(current['published_index'])} {_short_band(current['published_band'])}**. This replay does not rewrite that file. The 1.1.1 restatement changes only the two checklist cells.

## Current reading next to the stress months

The current row uses the 9 October 2026 published raws for inflation, unemployment, debt, and crime, and the 1.1.1 checklist for homelessness (**{_num(pins['homelessness_rate'], 2)}**, {pins['homelessness_observation_date']}) and trust (**{_num(pins['trust_in_government'], 0)}**, survey year {pins['trust_observation_date']}). Food is the shadow print **{_num(values['food_cpi_yoy'], 1)}** ({current['food_date']}). Prime-age EPOP is the shadow print **{_num(values['prime_age_epop'], 1)}** ({current['epop_date']}). Mortgage delinquency is **{_num(values['housing_delinquency'])}** ({current['housing_date']}, {current['housing_status']}). Rent burden is **{_num(values['rent_burden_30'], 1)}** ({current['rent_date']}, {current['rent_status']}). VIX is the week ending **{current['vix_week']}** mean **{_num(values['vix_month_mean'])}**. Credit conditions are the Chicago Fed print for **{current['credit_week']}**, **{_num(values['credit_conditions'], 3)}**.

August 2026 in the monthly file is a different row: unemployment is the August print 4.1, EPOP is 80.4, and VIX is the August monthly mean. Crime on both rows is the April 2026 Nationwide Full Sample rate **{_num(apr_2026['incident_rate'])}**, carried forward after the RTCI file ends. The unweighted agency mean that month is **{_num(apr_2026['incident_unweighted'])}** and is not scored.

{chr(10).join(comparison)}

Bands are the live bands from `interpret`: High at or above 70, Moderate at or above 55, Low at or above 40, Critical below 40. Applying those bands to a wider basket is part of the research. The thresholds were not retuned.

## What the three baskets are

Every basket starts from the six live inputs and their live weights. The weights sum to 0.72 before any add-on. Each add-on has raw weight **0.08**. When an input is missing, its weight drops out and the denominator shrinks. The index is `Σ(normalized × weight) / Σ weight`, the same rule as `compute_index`. v1 component scores in the `v1_111` column are `compute_index` itself.

{chr(10).join(weight_lines)}

Basket A is the live score plus food CPI and prime-age EPOP. Basket B is the live score plus food CPI, mortgage delinquency, and the ACS 30%+ rent-burden share. Basket C is the live score plus the VIX monthly mean and the Chicago Fed NFCI credit subindex. Food is in both A and B so the 2022 food spike is visible in the cost-of-living basket and in the labor basket. The 0.70 × EPOP + 0.30 × participation blend from hypothesis h2 is not used.

Prime-age EPOP in the BLS fixture runs **{_num(epop_values[epop_low], 1)}** ({epop_low}) to **{_num(epop_values[epop_high], 1)}** ({epop_high}). The Chicago Fed credit file in this replay runs **{_num(credit_values[credit_low], 3)}** ({credit_low}) to **{_num(credit_values[credit_high], 3)}** ({credit_high}). The −4 to 4 credit range sits outside that file. It was not chosen to push the current reading under 70.

### Why the credit input is not an ICE spread

ICE BofA high-yield OAS (`BAMLH0A0HYM2`) and Moody's seasoned Baa yield are the usual credit-spread prints. Both licenses forbid copying the series into this repository. FRED's ICE history is also a rolling three-year window as of April 2026, so that file cannot cover 2008. Basket C uses the Chicago Fed NFCI credit subindex (`NFCICREDIT`), which the Chicago Fed publishes as a weekly credit-conditions index (average 0, standard deviation 1 since 1971). Positive means tighter than that average. It is built from credit-condition measures. It is not a bond spread in percentage points, and it is not labeled as one.

### What hypothesis h2 did

h2 is the previous labeled basket on this branch: CPI, food, a labor blend, VIX, and an unweighted crime trial. Debt, homelessness, and trust were out. Those six months are the prior committed replay. This command does not recompute them.

{chr(10).join(h2_lines)}

August 2026 on h2 was **77.28 High** against a v1 held-constant score of **57.11 Moderate**. The gap was the basket. A calm labor blend and a calm VIX replaced unemployment, and the three slower stressed series were gone. Keeping those three series is why the current 1.1.1 reading and all three new baskets stay in Moderate.

## Full history and the stress windows

The monthly file is every month from January 2007 through August 2026 for which the BLS CPI fixture can form a year-over-year rate. October 2025 stays blank for CPI, food, unemployment, and EPOP. Debt is the quarterly `GFDEGDQ188S` file fetched {DEBT_FULL_PULL_DATE}, and it covers this span, so 2022 is no longer a debt gap. The earlier h2 note excluded 2022–2025 Q3 debt because that fixture did not contain the quarters. Crime is the population-weighted Nationwide Full Sample rate. Before January 2018 the weight drops out. From May 2026 through August 2026 the April 2026 rate is carried forward and labeled `carried_forward`.

{chr(10).join(range_lines)}

{chr(10).join(band_lines)}

No month in this file is High on v1 or on A, B, or C. No month is Critical.

Basket B's full-history low is {_cell(sep_2011, 'b_index')} on {sep_2011['date']}. Rent burden that month is the 2011 survey peak {_num(sep_2011['rent_burden_30'], 1)} ({sep_2011['rent_observation_date']}), and mortgage delinquency is {_num(sep_2011['housing_delinquency'])}. Unemployment is {_num(sep_2011['unemployment_rate'], 1)}. 1.1.1 is {_cell(sep_2011, 'v1_111_index')}. The two household add-ons are stressed at once, and that is what pushes B below v1.

## Composition

Component scores use the ranges above. A component above the 1.1.1 reading pulls a basket up. A component below it pulls the basket down. The displayed component is rounded to two decimals. The index uses the unrounded component, then rounds the quotient, the same way `compute_index` does.

**Current reading ({current['publication_date']}).** 1.1.1 is {_num(v1_now)} {_short_band(scored['v1']['band'])}. Food {_direction(a_norms.get('food_cpi_yoy'), v1_now)}. Prime-age EPOP {_direction(a_norms.get('prime_age_epop'), v1_now)}. Mortgage delinquency {_direction(b_norms.get('housing_delinquency'), v1_now)}. Rent burden {_direction(b_norms.get('rent_burden_30'), v1_now)}. VIX {_direction(c_norms.get('vix_month_mean'), v1_now)}. Credit conditions {_direction(c_norms.get('credit_conditions'), v1_now)}. The lift in A is mostly EPOP near the top of 68–82. The lift in B is the calm delinquency print overpowering a rent-burden score that does sit below the index. The lift in C is a calm VIX. Credit is about average on the −4 to 4 range and barely moves the reading. None of that is a claim that household stress fell inside the six live inputs.

**October 2008.** 1.1.1 is {_cell(oct_2008, 'v1_111_index')}. Unemployment is {_num(oct_2008['unemployment_rate'], 1)} and crime is excluded, so the financial spike is outside v1. Basket C is {_cell(oct_2008, 'c_index')}. VIX {_direction(oct_2008['vix_normalized'], oct_2008['v1_111_index'])}. Credit {_direction(oct_2008['credit_normalized'], oct_2008['v1_111_index'])}. That is the month C is for. Basket A is {_cell(oct_2008, 'a_index')}: EPOP was still {_num(oct_2008['prime_age_epop'], 1)} and {_direction(oct_2008['epop_normalized'], oct_2008['v1_111_index'])}. Basket B is {_cell(oct_2008, 'b_index')}. Mortgage delinquency was {_num(oct_2008['housing_delinquency'])}, already rising, and the rent-burden print is the 2008 survey carried from January.

**October 2009.** 1.1.1 is {_cell(oct_2009, 'v1_111_index')} with unemployment {_num(oct_2009['unemployment_rate'], 1)}. Basket B is {_cell(oct_2009, 'b_index')} because mortgage delinquency is {_num(oct_2009['housing_delinquency'])} and {_direction(oct_2009['housing_normalized'], oct_2009['v1_111_index'])}. Basket A is {_cell(oct_2009, 'a_index')}. Food CPI was {_num(oct_2009['food_cpi_yoy'], 1)} and {_direction(oct_2009['food_normalized'], oct_2009['v1_111_index'])}. That food add-on makes the unemployment-peak month look calmer. EPOP at {_num(oct_2009['prime_age_epop'], 1)} {_direction(oct_2009['epop_normalized'], oct_2009['v1_111_index'])}. Basket C is {_cell(oct_2009, 'c_index')}: the VIX spike was over, and credit had eased, so C does not mark the labor trough of the recession.

**December 2009.** 1.1.1 is {_cell(dec_2009, 'v1_111_index')} with crime still excluded. The 1.0.0 held-constant column, which pins crime at 2723, is {_cell(dec_2009, 'v1_100_held_index')}. Part of the gap is the missing crime history. A calm pinned crime rate adds weight on the stable side of the scale. That Low reading is not a 2009 crime spike.

**April 2020.** 1.1.1 is {_cell(apr_2020, 'v1_111_index')} (unemployment {_num(apr_2020['unemployment_rate'], 1)}, Nationwide Full Sample crime {_num(apr_2020['incident_rate'])}). The inflation-unemployment-debt partial, the same three-input replay as the locked v1.0.0 harness, is {_cell(apr_2020, 'v1_partial_index')}. The 1.0.0 pins on those FRED inputs are {_cell(apr_2020, 'v1_100_held_index')}. Basket A is {_cell(apr_2020, 'a_index')}. EPOP was {_num(apr_2020['prime_age_epop'], 1)} and {_direction(apr_2020['epop_normalized'], apr_2020['v1_111_index'])}. A marks the labor break harder than v1. Basket B is {_cell(apr_2020, 'b_index')}. Mortgage delinquency was {_num(apr_2020['housing_delinquency'])} and {_direction(apr_2020['housing_normalized'], apr_2020['v1_111_index'])}. Rent burden is the 2019 survey carried forward ({_num(apr_2020['rent_burden_30'], 1)}, {apr_2020['rent_observation_date']}), the low in this ACS file, and {_direction(apr_2020['rent_normalized'], apr_2020['v1_111_index'])}. Bank delinquency did not show the COVID labor shock. Forbearance kept the series calm, and that calm series pulls B back to Moderate. Basket C is {_cell(apr_2020, 'c_index')}. VIX and credit were stressed, and both sit below the 1.1.1 reading, so C stays in Low with v1.

**June 2022.** 1.1.1 is {_cell(jun_2022, 'v1_111_index')} with headline CPI {_num(jun_2022['inflation_rate'])} and debt {_num(jun_2022['debt_to_gdp_ratio'])} ({jun_2022['debt_observation_date']}, {jun_2022['debt_status']}). Food CPI was {_num(jun_2022['food_cpi_yoy'], 1)} and {_direction(jun_2022['food_normalized'], jun_2022['v1_111_index'])}. EPOP was {_num(jun_2022['prime_age_epop'], 1)} and {_direction(jun_2022['epop_normalized'], jun_2022['v1_111_index'])}. Those two add-ons pull in opposite directions, and basket A is {_cell(jun_2022, 'a_index')}, a small step above v1 rather than a deeper inflation reading. Basket B is {_cell(jun_2022, 'b_index')}. Mortgage delinquency was {_num(jun_2022['housing_delinquency'])} and {_direction(jun_2022['housing_normalized'], jun_2022['v1_111_index'])}, which offsets food and the rent-burden score ({_num(jun_2022['rent_normalized'])}). Basket C is {_cell(jun_2022, 'c_index')}. VIX {_direction(jun_2022['vix_normalized'], jun_2022['v1_111_index'])}. Credit {_direction(jun_2022['credit_normalized'], jun_2022['v1_111_index'])}. 2022 was an inflation year. It was not a 2008-style credit break, and C does not treat it as one.

**October 2025.** CPI, food, unemployment, and EPOP are blank. 1.1.1 is {_cell(oct_2025, 'v1_111_index')} on debt, crime, homelessness, and trust (`{oct_2025['v1_111_inputs_present']}`). The inflation-unemployment-debt partial has only the debt print that month and is {_cell(oct_2025, 'v1_partial_index')}. Basket A is {_cell(oct_2025, 'a_index')}, the same number as 1.1.1, because both of its add-ons are missing and the denominator does not change. Baskets B and C are {_cell(oct_2025, 'b_index')} and {_cell(oct_2025, 'c_index')}. Calm delinquency and a calm VIX are still present, so they lift a thin month. That is not a recovery.

## Weekly volatility

A Friday publish of methodology 1.1.1, basket A, or basket B does not move inside a calendar month in this vintage. Inflation, unemployment, food, and EPOP update monthly. Debt, delinquency, and rent burden are quarterly or annual and are carried inside the month. Homelessness and trust are the held checklist. Crime is a monthly file rate. Across {v1_within['weeks']} within-month Friday pairs, v1, A, and B are flat on every pair (share flat {_num(float(v1_within['share_flat']) * 100, 1)}%, mean absolute move {_num(v1_within['mean_abs_change'], 2)}).

Basket C is the weekly series. The credit subindex is a Friday print, and the VIX slot uses that week's mean close. Within-month, the mean absolute move is **{_num(c_within['mean_abs_change'], 2)}**, the standard deviation of the signed move is **{_num(c_within['stdev_change'], 2)}**, and {_num(float(c_within['share_flat']) * 100, 1)}% of those pairs are flat at two decimals. The largest within-month move is **{_num(c_within['max_abs_change'])}** on the week of {c_within['max_abs_week']}. Inside the 2008 window the largest within-month drop is **{_num(c_2008['max_drop'])}** on the week of {c_2008['max_drop_week']}.

The `all_fridays` sample also counts the step into a new month, which is when a new CPI or unemployment print arrives. For v1 that mean absolute Friday-to-Friday move is **{_num(v1_all['mean_abs_change'], 2)}** and the largest step is **{_num(v1_all['max_abs_change'])}** on the week of {v1_all['max_abs_week']}. That step is a monthly update landing on a Friday, not a week of market noise.

{chr(10).join(weekly_lines)}

This path uses the revised vintage. A Friday in 2008 is scored with the revised print for that month, not with the print that had been published by that Friday. It is not an ALFRED real-time path.

## Cadence, freshness, and source reliability

Freshness is measured against this research pull. The BLS, household, rent, and monthly VIX fixtures are the {DATA_PULL_DATE} / 2026-09-27 pull. Debt, the credit subindex, and the weekly VIX file were added {DEBT_FULL_PULL_DATE}. The current row's inflation, unemployment, crime, debt, food, and EPOP are the values already in the committed `latest.json` shadows and metrics.

| Input | Cadence | Latest observation used | Freshness | Reliability |
| --- | --- | --- | --- | --- |
| Headline CPI | Monthly | {current['inflation_date']} | About six weeks behind a 9 October publication. October 2025 is a real publication gap and stays blank. | BLS CPI-U via the same series as the live fetcher. Revised vintage, not ALFRED. |
| Unemployment | Monthly | {current['unemployment_date']} | The October publication has the September print. The monthly file ends August 2026. | BLS `UNRATE`. Revised vintage. |
| Crime | Monthly file, published as the latest month | {current['incident_date']} | The 9 October week still carries April 2026. About five months of lag. | RTCI Nationwide Full Sample, population-weighted violent plus property per 100,000. 621 agencies in this file, a balanced sample, not a census of every U.S. agency. No fair rate before January 2018. |
| Debt-to-GDP | Quarterly | {current['debt_date']} | 2026 Q1, carried into October. The next quarter is not in this file. | FRED `GFDEGDQ188S`, OMB debt and BEA GDP, constructed by the St. Louis Fed. Revised. Overlap with the locked 2026-09-23 crisis fixture matches. |
| Homelessness | Annual checklist | {pins['homelessness_observation_date']} | 2025 AHAR point-in-time count. Held on every historical month. | HUD AHAR. The checklist value is 0.22. There is no monthly history. |
| Trust | Annual checklist | {pins['trust_observation_date']} | Edelman survey year 2026. Held on every historical month. | Edelman Trust Barometer, United States, Government. A private barometer with a year stamp, not a statistical-agency microdata release. There is no monthly history. |
| Food CPI | Monthly | {current['food_date']} | Same lag and the same October 2025 gap as headline CPI. | BLS `CPIUFDNS` / `CUUR0000SAF1`, the food shadow. Not in the live score. |
| Prime-age EPOP | Monthly | {current['epop_date']} | September 2026 on the live shadow. The monthly fixture ends August. | BLS `LNS12300060`. Not in the live score. |
| Mortgage delinquency | Quarterly | {current['housing_date']} | 2026 Q2, carried into October. | Federal Reserve CHGDEL, residential column, all commercial banks. It misses household forbearance, which is why April 2020 stays calm. |
| Rent burden | Annual | {current['rent_date']} | 2024 ACS 1-year, carried into 2026. No 2020 standard 1-year and no 2025 1-year in this file. | Census ACS `B25070`, national, 30%+ of income. A real household measure. Too slow to move a weekly score, and the latest year is stale. |
| VIX | Daily; scored as a week or month mean | {current['vix_week']} | The week of the 9 October publication. Close on 9 October 2026 is in the CBOE file. | CBOE `VIX_History.csv`, the series FRED publishes as `VIXCLS`. An equity-volatility index, not a credit spread. |
| Credit conditions | Weekly, Friday | {current['credit_week']} | One week behind the 9 October publication. | Chicago Fed NFCI credit subindex. Public index, revised, not a licensed OAS series. |

## What still blocks a v2.0 contract

- The recommendation is to keep publishing methodology 1.1.1. The weights and ranges above are the baskets that were scored. They were not fit to a loss, a utility function, or a band boundary.
- Basket A lifts today's reading because prime-age employment is strong, and it makes October 2009 look calmer because food prices were falling. It does mark April 2020.
- Basket B marks the 2009 delinquency peak and September 2011, when the rent-burden peak and a 10.5 delinquency print land together. It then treats April 2020 as Moderate, because the bank series did not see the labor break. Rent burden is a flat annual share. The 2024 survey is still the latest print.
- Basket C marks October 2008 and moves every week. It does not mark 2022 inflation, and a calm VIX lifts the current reading. The credit series is a conditions index, not a corporate spread. ICE OAS and Moody's Baa were not copied.
- Homelessness and trust still have no monthly history. Holding the 1.1.1 checklist on 2008 and 2020 is a level shift, not a path for those series.
- Crime has no fair pre-2018 path. Carrying April 2026 into later months copies the live publisher's "latest file month" rule. It is not an August crime observation.
- The pull is a current revised vintage. A 2008 row is not the print available during 2008.
- Companions stay outside the score.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.v2_candidate --check-locked
```

That reprints the locked 57.11 line and the 1.1.1 restatement, and rewrites the CSV files, this note, and the chart. It does not run the weekly publisher.

`python -m runtime.backtest` remains the v1.0.0-only replay. The v2 command does not replace it.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
"""
    return text


def render_svg(rows: Sequence[Mapping[str, object]]) -> str:
    """Four line charts: full history and the three stress windows."""
    width = 760
    height = 210
    left = 48
    right = 16
    top = 28
    bottom = 36
    colors = {
        "v1_111_index": "#1d4e89",
        "a_index": "#b45309",
        "b_index": "#7c3aed",
        "c_index": "#0f766e",
    }
    panels_spec = (
        ("all", "Full history"),
        ("2008", "2008 window"),
        ("2020", "2020 window"),
        ("2022", "2022 inflation year"),
    )
    panels = []
    for index, (window_name, title) in enumerate(panels_spec):
        if window_name == "all":
            subset = list(rows)
        else:
            subset = [row for row in rows if row["window"] == window_name]
        y0 = index * height
        values = []
        for key in colors:
            for row in subset:
                if row[key] is not None:
                    values.append(float(row[key]))
        lo = min(values) - 2 if values else 40
        hi = max(values) + 2 if values else 80
        if hi <= lo:
            hi = lo + 1
        plot_w = width - left - right
        plot_h = height - top - bottom

        def xy(i: int, value: float, y_origin: float = y0, low: float = lo, high: float = hi) -> tuple[float, float]:
            x = left + (plot_w * i / max(len(subset) - 1, 1))
            y = y_origin + top + (high - value) / (high - low) * plot_h
            return x, y

        lines = []
        for key, color in colors.items():
            points = []
            for i, row in enumerate(subset):
                if row[key] is None:
                    if points:
                        lines.append((color, points))
                        points = []
                    continue
                points.append(xy(i, float(row[key])))
            if points:
                lines.append((color, points))
        path_markup = []
        for color, points in lines:
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            path_markup.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="1.6" points="{coords}"/>'
            )
        start = subset[0]["date"]
        end = subset[-1]["date"]
        panels.append(
            f'<text x="{left}" y="{y0 + 16}" font-size="13" font-family="sans-serif">{title} ({start} to {end})</text>'
            f'<line x1="{left}" y1="{y0 + top}" x2="{left}" y2="{y0 + top + plot_h}" stroke="#ccc"/>'
            f'<line x1="{left}" y1="{y0 + top + plot_h}" x2="{width - right}" y2="{y0 + top + plot_h}" stroke="#ccc"/>'
            + "".join(path_markup)
            + f'<text x="{left}" y="{y0 + height - 12}" font-size="11" font-family="sans-serif" fill="#555">{_num(lo)}–{_num(hi)} on the index scale</text>'
        )
    legend = (
        f'<text x="{left}" y="{len(panels_spec) * height - 4}" font-size="11" font-family="sans-serif">'
        '<tspan fill="#1d4e89">v1 1.1.1</tspan>'
        '<tspan fill="#b45309">   A labor and food</tspan>'
        '<tspan fill="#7c3aed">   B cost of living</tspan>'
        '<tspan fill="#0f766e">   C financial stress</tspan>'
        "</text>"
    )
    body = "".join(panels) + legend
    total_h = len(panels_spec) * height
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" '
        f'viewBox="0 0 {width} {total_h}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>'
        f"{body}</svg>\n"
    )


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    bundle = load_v2_bundle()
    rows = build_v2_rows(bundle)
    summary = summarize(rows)
    weekly = weekly_volatility(bundle)
    current = current_reading(bundle)
    monthly = output_dir / MONTHLY_NAME
    summary_path = output_dir / SUMMARY_NAME
    weekly_path = output_dir / WEEKLY_NAME
    chart_path = output_dir / CHART_NAME
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    write_monthly(rows, monthly)
    write_summary(summary, summary_path)
    write_weekly(weekly, weekly_path)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_text(render_svg(rows), encoding="utf-8")
    note.write_text(
        render_markdown(rows, summary, weekly, current, bundle),
        encoding="utf-8",
    )
    return [monthly, summary_path, weekly_path, chart_path, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.v2_candidate",
        description=(
            "Score methodology 1.1.1 beside three research baskets. "
            "Does not publish the weekly score."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for the monthly CSV, summary CSV, weekly CSV, and chart",
    )
    parser.add_argument(
        "--note",
        type=Path,
        default=PACKAGE_DIR / NOTE_NAME,
        help="Markdown results note",
    )
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
            f"{current['publication_date']} {current['scored']['v1']['index']:.2f} "
            f"{current['scored']['v1']['band']} methodology 1.1.1 restatement"
        )
    for path in write_outputs(args.output, args.note):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
