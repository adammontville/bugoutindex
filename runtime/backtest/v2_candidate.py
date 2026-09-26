# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Trial v2 candidate replay beside the locked v1.0.0 FRED replay.

This module does not publish a score. It does not change
``runtime.processing.formula``, the weekly job, or ``docs/data/latest.json``.
The v1 numbers in the output are ``compute_index``. The v2 numbers are a
labeled hypothesis basket scored with ``formula.normalize`` and the same
divide-by-sum-of-present-weights rule. They are not a methodology version.
"""
from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Mapping, Optional, Sequence

from runtime.backtest.harness import (
    FIXTURE_DOWNLOAD_DATE,
    HELD_CONSTANT_BASELINE,
    PUBLISHED_DATE,
    WINDOWS,
    FredLevels,
    Window,
    build_month_row,
    cpi_yoy,
    format_float,
    iter_months,
    load_fixtures,
    load_published_raws,
    prior_year_date,
    score_published_inputs,
)
from runtime.data.fetch.fetch_incident_rate import PUBLISHED_INCIDENT_RATE
from runtime.processing.formula import compute_index, interpret, normalize

CANDIDATE_LABEL = "v2_candidate_hypothesis"
DATA_PULL_DATE = "2026-09-26"
# BLS cells for this month were non-numeric in the 2026-09-26 pull.
BLS_GAP_MONTH = "2025-10-01"

# Hypothesis weights. They sum to 1.00 when every trial input is present.
# They are not formula.WEIGHTS and they are not a fitted contract.
TRIAL_WEIGHTS = {
    "inflation_rate": 0.22,
    "food_cpi_yoy": 0.14,
    "labor_utilization": 0.28,
    "vix_month_mean": 0.18,
    "incident_rate": 0.18,
}
PRIMARY_ORDER = (
    "inflation_rate",
    "food_cpi_yoy",
    "labor_utilization",
    "vix_month_mean",
    "incident_rate",
)
# Endpoints are hypotheses except where the note says they reuse v1.0.0
# or the incubating food draft. Higher raw is less stable unless INVERSE.
TRIAL_RANGES = {
    "inflation_rate": (-10.0, 15.0),
    "food_cpi_yoy": (0.0, 10.0),
    "labor_utilization": (70.0, 83.0),
    "prime_age_epop": (68.0, 82.0),
    "vix_month_mean": (10.0, 65.0),
    "incident_rate": (500.0, 8000.0),
    "unemployment_rate": (0.0, 25.0),
    "debt_to_gdp_ratio": (0.0, 200.0),
}
INVERSE = frozenset({"labor_utilization", "prime_age_epop"})
LABOR_EPOP_WEIGHT = 0.70
LABOR_LFPR_WEIGHT = 0.30
DEBT_SENSITIVITY_WEIGHT = 0.12
LABOR_SLOT_WEIGHT = TRIAL_WEIGHTS["labor_utilization"]

RECENT_WINDOW = Window(
    name="recent",
    start="2022-01-01",
    end="2026-08-01",
    description=(
        "January 2022 through August 2026. August 2026 is the last headline "
        "CPI month in this pull and the month behind the locked 57.11 score. "
        "The window includes the 2022 food and headline inflation peak."
    ),
)
V2_WINDOWS = {
    "2008": WINDOWS["2008"],
    "2020": WINDOWS["2020"],
    "recent": RECENT_WINDOW,
}
V2_WINDOW_ORDER = ("2008", "2020", "recent")

PACKAGE_DIR = Path(__file__).resolve().parent
V2_FIXTURE_DIR = PACKAGE_DIR / "fixtures" / "v2"
OUTPUT_DIR = PACKAGE_DIR / "output"
MONTHLY_NAME = "v2_candidate_monthly.csv"
SUMMARY_NAME = "v2_candidate_summary.csv"
NOTE_NAME = "V2_CANDIDATE.md"
CHART_NAME = "v2_candidate_chart.svg"

SCORE_NOTE = (
    "Hypothesis replay for methodology v2.0 planning. Trial weights and "
    "ranges are not a contract. v1 columns are compute_index (methodology "
    "1.0.0). v2 columns are not the published BugOut Index and are not "
    "inputs to the weekly job."
)

SUMMARY_SCENARIOS = (
    ("v1_partial", "v1.0.0 partial (crime, homelessness, trust excluded)"),
    ("v1_held", "v1.0.0 held constant (2723 / 0.23 / 41)"),
    ("v1_held_without_debt", "v1.0.0 held, debt removed"),
    ("v1_held_without_homelessness", "v1.0.0 held, homelessness removed"),
    ("v1_held_without_trust", "v1.0.0 held, trust removed"),
    ("v1_partial_without_debt", "v1.0.0 partial, debt also removed"),
    ("v2", "v2 candidate (crime trial when the RTCI month exists)"),
    ("v2_without_crime", "v2 candidate with crime always excluded"),
    ("v2_if_unrate", "v2 basket with UNRATE instead of the labor composite"),
    ("v2_if_epop_only", "v2 basket with prime-age EPOP instead of the composite"),
    ("v2_if_debt_included", "v2 basket plus debt-to-GDP at weight 0.12"),
    ("v2_if_crime_held", "v2 basket with crime held at the locked 2723"),
)

KEY_MONTHS = (
    ("2007-12-01", "Great Recession window starts"),
    ("2008-10-01", "VIX monthly mean jumps"),
    ("2008-11-01", "VIX monthly-mean peak in this pull"),
    ("2009-10-01", "UNRATE peak in the locked vintage (10.0)"),
    ("2009-12-01", "Great Recession window ends"),
    ("2020-01-01", "Pre-COVID month"),
    ("2020-03-01", "COVID VIX monthly-mean peak"),
    ("2020-04-01", "COVID unemployment and prime-age EPOP trough"),
    ("2020-12-01", "COVID window ends"),
    ("2022-06-01", "Food CPI year-over-year above the 10% draft"),
    ("2022-09-01", "Food CPI year-over-year high in this pull"),
    ("2025-10-01", "BLS publication gap in this pull"),
    ("2026-04-01", "Last month in the RTCI trial file"),
    ("2026-08-01", "Latest headline CPI month; locked-score inputs"),
)


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


def labor_utilization(epop: Optional[float], lfpr: Optional[float]) -> Optional[float]:
    """Hypothesis blend: 0.70 × prime-age EPOP + 0.30 × prime-age LFPR.

    This is not the incubating essay's participation penalty. That penalty
    was never given a formula. Both series move this input every month.
    """
    if epop is None or lfpr is None:
        return None
    return LABOR_EPOP_WEIGHT * float(epop) + LABOR_LFPR_WEIGHT * float(lfpr)


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
    crime = {}
    with (folder / "RTCI_monthly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            crime[row["observation_date"]] = {
                "unweighted": float(row["incident_rate_unweighted"]),
                "population_weighted": float(row["incident_rate_population_weighted"]),
                "agencies": int(row["agencies"]),
            }
    extra_debt = _as_float_map(_load_text_series(folder / "GFDEGDQ188S_published_extra.csv"))
    return {
        "cpi": _load_text_series(folder / "CPIAUCSL.csv"),
        "food": _load_text_series(folder / "CPIUFDNS.csv"),
        "epop": _as_float_map(_load_text_series(folder / "LNS12300060.csv")),
        "lfpr": _as_float_map(_load_text_series(folder / "LNS11300060.csv")),
        "unrate": _as_float_map(_load_text_series(folder / "LNS14000000.csv")),
        "vix": vix_rows,
        "crime": crime,
        "extra_debt": extra_debt,
    }


def recent_debt_map(fixture_debt: Mapping[str, float], extra_debt: Mapping[str, float]) -> dict[str, float]:
    """Debt prints that may be used on the recent window.

    Pre-2025 fixture quarters are left out so 2022 is not scored on a
    2020 print carried across several years. The 2026-01-01 fixture print
    and the published 2025-10-01 extra print are kept.
    """
    debt = {day: value for day, value in fixture_debt.items() if day >= "2025-01-01"}
    debt.update(extra_debt)
    return debt


def v1_levels_for(window_name: str, bundle: Mapping, fixture: FredLevels) -> tuple[FredLevels, str]:
    """Locked fixture for the crisis windows. BLS fill only on ``recent``."""
    if window_name in ("2008", "2020"):
        return fixture, "locked_fred_fixture_2026-09-23"
    if window_name != "recent":
        raise KeyError(window_name)
    return (
        FredLevels(
            cpi=_as_float_map(bundle["cpi"]),
            unemployment=dict(bundle["unrate"]),
            debt_to_gdp=recent_debt_map(fixture.debt_to_gdp, bundle["extra_debt"]),
        ),
        "bls_pull_2026-09-26_plus_published_debt",
    )


def score_basket(
    values: Mapping[str, Optional[float]],
    order: Sequence[str],
    weights: Mapping[str, float],
) -> dict:
    """Normalize, then divide by the sum of weights that were present.

    A missing input shrinks the denominator. It is not treated as zero
    stress. An empty basket returns a null index, not a collapse score.
    """
    total_weighted = 0.0
    total_weight = 0.0
    present = []
    excluded = []
    metrics = {}
    for name in order:
        raw = values.get(name)
        if raw is None or not isinstance(raw, (int, float)):
            excluded.append(name)
            metrics[name] = {"raw": None, "normalized": None, "weight": weights[name]}
            continue
        lo, hi = TRIAL_RANGES[name]
        norm = normalize(float(raw), lo, hi, inverse=name in INVERSE)
        metrics[name] = {
            "raw": float(raw),
            "normalized": round(norm, 2),
            "weight": weights[name],
        }
        total_weighted += norm * weights[name]
        total_weight += weights[name]
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
        "metrics": metrics,
    }


def _v1_index(raws: Mapping[str, Optional[float]]) -> tuple[Optional[float], str]:
    """Locked formula on a subset of the six core inputs."""
    payload = {}
    for metric, value in raws.items():
        if value is None or not isinstance(value, (int, float)):
            continue
        payload[metric] = {"data": {metric: float(value)}}
    if not payload:
        return None, ""
    scored = compute_index(payload)
    return scored["index"], interpret(scored["index"])["band"]


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


def _primary_values(day: str, bundle: Mapping, inflation: Optional[float]) -> dict:
    epop = bundle["epop"].get(day)
    lfpr = bundle["lfpr"].get(day)
    vix = bundle["vix"].get(day)
    crime = bundle["crime"].get(day)
    return {
        "inflation_rate": inflation,
        "food_cpi_yoy": _food_from_texts(bundle["food"], day),
        "labor_utilization": labor_utilization(epop, lfpr),
        "vix_month_mean": None if vix is None else vix["mean"],
        "incident_rate": None if crime is None else crime["unweighted"],
        "prime_age_epop": epop,
        "prime_age_lfpr": lfpr,
        "unemployment_rate": bundle["unrate"].get(day),
        "vix_month_max": None if vix is None else vix["max"],
        "crime": crime,
    }


def _weights_for(order: Sequence[str], labor_name: str = "labor_utilization") -> dict[str, float]:
    weights = {}
    for name in order:
        if name == labor_name or name in ("unemployment_rate", "prime_age_epop"):
            weights[name] = LABOR_SLOT_WEIGHT
        elif name == "debt_to_gdp_ratio":
            weights[name] = DEBT_SENSITIVITY_WEIGHT
        else:
            weights[name] = TRIAL_WEIGHTS[name]
    return weights


def build_v2_rows(bundle: Optional[Mapping] = None, fixture: Optional[FredLevels] = None) -> list[dict]:
    """One row per month of the 2008, 2020, and recent windows."""
    bundle = load_v2_bundle() if bundle is None else bundle
    fixture = load_fixtures() if fixture is None else fixture
    rows = []
    for name in V2_WINDOW_ORDER:
        window = V2_WINDOWS[name]
        levels, source = v1_levels_for(name, bundle, fixture)
        download = FIXTURE_DOWNLOAD_DATE if source.startswith("locked_") else DATA_PULL_DATE
        for day in iter_months(window.start, window.end):
            partial = build_month_row(levels, day, window, "partial", fred_download_date=download)
            held = build_month_row(levels, day, window, "held_constant", fred_download_date=download)
            inflation = _inflation_from_texts(bundle["cpi"], day)
            parts = _primary_values(day, bundle, inflation)
            crime = parts["crime"]
            primary = score_basket(parts, PRIMARY_ORDER, _weights_for(PRIMARY_ORDER))
            without_crime_values = dict(parts)
            without_crime_values["incident_rate"] = None
            without_crime = score_basket(
                without_crime_values, PRIMARY_ORDER, _weights_for(PRIMARY_ORDER)
            )
            unrate_order = tuple(
                "unemployment_rate" if metric == "labor_utilization" else metric
                for metric in PRIMARY_ORDER
            )
            unrate_values = dict(parts)
            unrate_values["unemployment_rate"] = parts["unemployment_rate"]
            if_unrate = score_basket(unrate_values, unrate_order, _weights_for(unrate_order))
            epop_order = tuple(
                "prime_age_epop" if metric == "labor_utilization" else metric
                for metric in PRIMARY_ORDER
            )
            if_epop = score_basket(parts, epop_order, _weights_for(epop_order))
            debt_raw = held["debt_to_gdp_ratio"]
            debt_order = PRIMARY_ORDER + ("debt_to_gdp_ratio",)
            debt_values = dict(parts)
            debt_values["debt_to_gdp_ratio"] = debt_raw
            if_debt = score_basket(debt_values, debt_order, _weights_for(debt_order))
            held_crime_values = dict(parts)
            held_crime_values["incident_rate"] = float(PUBLISHED_INCIDENT_RATE)
            if_crime_held = score_basket(
                held_crime_values, PRIMARY_ORDER, _weights_for(PRIMARY_ORDER)
            )

            def demote(raws: Mapping[str, Optional[float]]) -> tuple[Optional[float], str]:
                return _v1_index(raws)

            without_debt_held = demote(
                {
                    "inflation_rate": held["inflation_rate"],
                    "unemployment_rate": held["unemployment_rate"],
                    "incident_rate": held["incident_rate"],
                    "homelessness_rate": held["homelessness_rate"],
                    "trust_in_government": held["trust_in_government"],
                }
            )
            without_homeless = demote(
                {
                    "inflation_rate": held["inflation_rate"],
                    "unemployment_rate": held["unemployment_rate"],
                    "debt_to_gdp_ratio": held["debt_to_gdp_ratio"],
                    "incident_rate": held["incident_rate"],
                    "trust_in_government": held["trust_in_government"],
                }
            )
            without_trust = demote(
                {
                    "inflation_rate": held["inflation_rate"],
                    "unemployment_rate": held["unemployment_rate"],
                    "debt_to_gdp_ratio": held["debt_to_gdp_ratio"],
                    "incident_rate": held["incident_rate"],
                    "homelessness_rate": held["homelessness_rate"],
                }
            )
            partial_without_debt = demote(
                {
                    "inflation_rate": partial["inflation_rate"],
                    "unemployment_rate": partial["unemployment_rate"],
                }
            )
            rows.append(
                {
                    "date": day,
                    "window": window.name,
                    "candidate_label": CANDIDATE_LABEL,
                    "methodology_reference": "1.0.0",
                    "data_pull_date": DATA_PULL_DATE,
                    "v1_level_source": source,
                    "v1_partial_index": partial["replay_index"],
                    "v1_partial_band": partial["band"],
                    "v1_held_index": held["replay_index"],
                    "v1_held_band": held["band"],
                    "v1_held_without_debt_index": without_debt_held[0],
                    "v1_held_without_debt_band": without_debt_held[1],
                    "v1_held_without_homelessness_index": without_homeless[0],
                    "v1_held_without_homelessness_band": without_homeless[1],
                    "v1_held_without_trust_index": without_trust[0],
                    "v1_held_without_trust_band": without_trust[1],
                    "v1_partial_without_debt_index": partial_without_debt[0],
                    "v1_partial_without_debt_band": partial_without_debt[1],
                    "v1_inflation_rate": partial["inflation_rate"],
                    "v1_unemployment_rate": partial["unemployment_rate"],
                    "v1_debt_to_gdp_ratio": partial["debt_to_gdp_ratio"],
                    "v1_debt_status": partial["debt_to_gdp_ratio_status"],
                    "v2_index": primary["index"],
                    "v2_band": primary["band"],
                    "v2_weight_denominator": primary["denominator"],
                    "v2_inputs_present": "|".join(primary["present"]),
                    "v2_inputs_excluded": "|".join(primary["excluded"]),
                    "v2_inflation_rate": parts["inflation_rate"],
                    "v2_inflation_normalized": primary["metrics"]["inflation_rate"]["normalized"],
                    "v2_food_cpi_yoy": parts["food_cpi_yoy"],
                    "v2_food_normalized": primary["metrics"]["food_cpi_yoy"]["normalized"],
                    "v2_labor_utilization": parts["labor_utilization"],
                    "v2_labor_normalized": primary["metrics"]["labor_utilization"]["normalized"],
                    "v2_prime_age_epop": parts["prime_age_epop"],
                    "v2_prime_age_lfpr": parts["prime_age_lfpr"],
                    "v2_vix_month_mean": parts["vix_month_mean"],
                    "v2_vix_normalized": primary["metrics"]["vix_month_mean"]["normalized"],
                    "v2_vix_month_max": parts["vix_month_max"],
                    "v2_incident_rate": parts["incident_rate"],
                    "v2_incident_normalized": primary["metrics"]["incident_rate"]["normalized"],
                    "v2_incident_status": "trial_observed" if crime else "excluded",
                    "v2_incident_agencies": None if crime is None else crime["agencies"],
                    "v2_incident_population_weighted": None
                    if crime is None
                    else crime["population_weighted"],
                    "v2_without_crime_index": without_crime["index"],
                    "v2_without_crime_band": without_crime["band"],
                    "v2_if_unrate_index": if_unrate["index"],
                    "v2_if_unrate_band": if_unrate["band"],
                    "v2_if_epop_only_index": if_epop["index"],
                    "v2_if_epop_only_band": if_epop["band"],
                    "v2_if_debt_included_index": if_debt["index"],
                    "v2_if_debt_included_band": if_debt["band"],
                    "v2_if_crime_held_index": if_crime_held["index"],
                    "v2_if_crime_held_band": if_crime_held["band"],
                    "score_note": SCORE_NOTE,
                }
            )
    return rows


COLUMNS = (
    "date",
    "window",
    "candidate_label",
    "methodology_reference",
    "data_pull_date",
    "v1_level_source",
    "v1_partial_index",
    "v1_partial_band",
    "v1_held_index",
    "v1_held_band",
    "v1_held_without_debt_index",
    "v1_held_without_debt_band",
    "v1_held_without_homelessness_index",
    "v1_held_without_homelessness_band",
    "v1_held_without_trust_index",
    "v1_held_without_trust_band",
    "v1_partial_without_debt_index",
    "v1_partial_without_debt_band",
    "v1_inflation_rate",
    "v1_unemployment_rate",
    "v1_debt_to_gdp_ratio",
    "v1_debt_status",
    "v2_index",
    "v2_band",
    "v2_weight_denominator",
    "v2_inputs_present",
    "v2_inputs_excluded",
    "v2_inflation_rate",
    "v2_inflation_normalized",
    "v2_food_cpi_yoy",
    "v2_food_normalized",
    "v2_labor_utilization",
    "v2_labor_normalized",
    "v2_prime_age_epop",
    "v2_prime_age_lfpr",
    "v2_vix_month_mean",
    "v2_vix_normalized",
    "v2_vix_month_max",
    "v2_incident_rate",
    "v2_incident_normalized",
    "v2_incident_status",
    "v2_incident_agencies",
    "v2_incident_population_weighted",
    "v2_without_crime_index",
    "v2_without_crime_band",
    "v2_if_unrate_index",
    "v2_if_unrate_band",
    "v2_if_epop_only_index",
    "v2_if_epop_only_band",
    "v2_if_debt_included_index",
    "v2_if_debt_included_band",
    "v2_if_crime_held_index",
    "v2_if_crime_held_band",
    "score_note",
)

_INDEX_COLUMNS = {
    "v1_partial_index",
    "v1_held_index",
    "v1_held_without_debt_index",
    "v1_held_without_homelessness_index",
    "v1_held_without_trust_index",
    "v1_partial_without_debt_index",
    "v2_index",
    "v2_weight_denominator",
    "v2_inflation_normalized",
    "v2_food_normalized",
    "v2_labor_normalized",
    "v2_vix_normalized",
    "v2_incident_normalized",
    "v2_without_crime_index",
    "v2_if_unrate_index",
    "v2_if_epop_only_index",
    "v2_if_debt_included_index",
    "v2_if_crime_held_index",
}
_ONE_DECIMAL = {"v2_food_cpi_yoy"}
_TWO_DECIMAL = {
    "v2_labor_utilization",
    "v2_vix_month_mean",
    "v2_vix_month_max",
    "v2_incident_rate",
    "v2_incident_population_weighted",
}


def csv_fields(row: Mapping[str, object]) -> dict[str, str]:
    rendered = {}
    for column in COLUMNS:
        value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in _INDEX_COLUMNS:
            rendered[column] = f"{float(value):.2f}"
        elif column in _ONE_DECIMAL:
            rendered[column] = f"{float(value):.1f}"
        elif column in _TWO_DECIMAL:
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


def summarize(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    """One summary row per scenario and window."""
    index_of = {
        "v1_partial": "v1_partial_index",
        "v1_held": "v1_held_index",
        "v1_held_without_debt": "v1_held_without_debt_index",
        "v1_held_without_homelessness": "v1_held_without_homelessness_index",
        "v1_held_without_trust": "v1_held_without_trust_index",
        "v1_partial_without_debt": "v1_partial_without_debt_index",
        "v2": "v2_index",
        "v2_without_crime": "v2_without_crime_index",
        "v2_if_unrate": "v2_if_unrate_index",
        "v2_if_epop_only": "v2_if_epop_only_index",
        "v2_if_debt_included": "v2_if_debt_included_index",
        "v2_if_crime_held": "v2_if_crime_held_index",
    }
    band_of = {key: column.replace("_index", "_band") for key, column in index_of.items()}
    summary = []
    for scenario, label in SUMMARY_SCENARIOS:
        for window_name in V2_WINDOW_ORDER:
            subset = [row for row in rows if row["window"] == window_name]
            ends = _extremes([(row["date"], row[index_of[scenario]]) for row in subset])
            counts = _band_counts(
                [
                    str(row[band_of[scenario]])
                    for row in subset
                    if row[index_of[scenario]] is not None
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


def _short_band(band: object) -> str:
    text = str(band or "")
    if not text:
        return "—"
    return (
        text.replace(" Stability", "")
        .replace(" Instability", "")
    )


def _num(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.{digits}f}"


def _by_date(rows: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    return {str(row["date"]): row for row in rows}


def _window_rows(rows: Sequence[Mapping[str, object]], window: str) -> list[Mapping[str, object]]:
    return [row for row in rows if row["window"] == window]


def _summary_lookup(summary: Sequence[Mapping[str, object]], scenario: str, window: str) -> Mapping[str, object]:
    for row in summary:
        if row["scenario"] == scenario and row["window"] == window:
            return row
    raise KeyError((scenario, window))


def _range_phrase(summary_row: Mapping[str, object]) -> str:
    return (
        f"{_num(summary_row['min_index'])} ({summary_row['min_date']}) to "
        f"{_num(summary_row['max_index'])} ({summary_row['max_date']})"
    )


def render_markdown(rows: Sequence[Mapping[str, object]], summary: Sequence[Mapping[str, object]]) -> str:
    """Results note. Numbers come from the rows just scored."""
    by_date = _by_date(rows)
    food_clamped = [
        row["date"]
        for row in rows
        if row["v2_food_cpi_yoy"] is not None and float(row["v2_food_cpi_yoy"]) > 10
    ]
    food_deflation = [
        row["date"]
        for row in rows
        if row["v2_food_cpi_yoy"] is not None and float(row["v2_food_cpi_yoy"]) < 0
    ]
    gfc_v1 = _summary_lookup(summary, "v1_partial", "2008")
    gfc_v1_held = _summary_lookup(summary, "v1_held", "2008")
    gfc_v2 = _summary_lookup(summary, "v2", "2008")
    covid_v1 = _summary_lookup(summary, "v1_partial", "2020")
    covid_v1_held = _summary_lookup(summary, "v1_held", "2020")
    covid_v2 = _summary_lookup(summary, "v2", "2020")
    recent_v2 = _summary_lookup(summary, "v2", "recent")
    april = by_date["2020-04-01"]
    march = by_date["2020-03-01"]
    oct_2009 = by_date["2009-10-01"]
    nov_2008 = by_date["2008-11-01"]
    aug_2026 = by_date["2026-08-01"]
    jun_2022 = by_date["2022-06-01"]
    sep_2022 = by_date["2022-09-01"]
    oct_2025 = by_date["2025-10-01"]
    apr_2026 = by_date["2026-04-01"]

    def cell(row: Mapping[str, object], index_key: str) -> str:
        band_key = index_key.replace("_index", "_band")
        if row[index_key] is None:
            return "—"
        return f"{_num(row[index_key])} {_short_band(row[band_key])}"

    key_lines = [
        "| Month | Why it is here | v1 partial | v1 held | v2 candidate | v2, crime off | v2, UNRATE instead | v2, debt added |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day, reason in KEY_MONTHS:
        row = by_date[day]
        key_lines.append(
            "| {day} | {reason} | {p} | {h} | {v} | {c} | {u} | {d} |".format(
                day=day,
                reason=reason,
                p=cell(row, "v1_partial_index"),
                h=cell(row, "v1_held_index"),
                v=cell(row, "v2_index"),
                c=cell(row, "v2_without_crime_index"),
                u=cell(row, "v2_if_unrate_index"),
                d=cell(row, "v2_if_debt_included_index"),
            )
        )

    summary_lines = [
        "| Window | v1 partial | v1 held | v2 candidate | v2, crime always off |",
        "| --- | --- | --- | --- | --- |",
    ]
    for window_name, title in (
        ("2008", "2008 (Dec 2007–Dec 2009)"),
        ("2020", "2020 (Jan–Dec)"),
        ("recent", "Recent (Jan 2022–Aug 2026)"),
    ):
        summary_lines.append(
            "| {title} | {a} | {b} | {c} | {d} |".format(
                title=title,
                a=_range_phrase(_summary_lookup(summary, "v1_partial", window_name)),
                b=_range_phrase(_summary_lookup(summary, "v1_held", window_name)),
                c=_range_phrase(_summary_lookup(summary, "v2", window_name)),
                d=_range_phrase(_summary_lookup(summary, "v2_without_crime", window_name)),
            )
        )

    band_lines = [
        "| Window | Scenario | High | Moderate | Low | Critical |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for window_name in V2_WINDOW_ORDER:
        for scenario in ("v1_partial", "v1_held", "v2", "v2_without_crime"):
            row = _summary_lookup(summary, scenario, window_name)
            band_lines.append(
                f"| {window_name} | {scenario} | {row['high']} | {row['moderate']} | {row['low']} | {row['critical']} |"
            )

    raw_lines = [
        "| Month | CPI YoY | Food YoY | Labor blend | EPOP | LFPR | UNRATE | VIX mean | VIX max | Crime trial |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day, _reason in KEY_MONTHS:
        row = by_date[day]
        crime_text = "excluded" if row["v2_incident_status"] != "trial_observed" else _num(row["v2_incident_rate"])
        raw_lines.append(
            "| {day} | {cpi} | {food} | {labor} | {epop} | {lfpr} | {un} | {vix} | {vmax} | {crime} |".format(
                day=day,
                cpi=_num(row["v2_inflation_rate"]),
                food=_num(row["v2_food_cpi_yoy"], 1),
                labor=_num(row["v2_labor_utilization"]),
                epop=_num(row["v2_prime_age_epop"], 1),
                lfpr=_num(row["v2_prime_age_lfpr"], 1),
                un=_num(row["v1_unemployment_rate"], 1),
                vix=_num(row["v2_vix_month_mean"]),
                vmax=_num(row["v2_vix_month_max"]),
                crime=crime_text,
            )
        )

    full_recent = _extremes(
        [
            (str(row["date"]), row["v2_index"])
            for row in rows
            if row["window"] == "recent" and abs(float(row["v2_weight_denominator"]) - 1.0) < 1e-9
        ]
    )
    april_without_debt = _num(april["v1_held_without_debt_index"])
    april_without_debt_band = _short_band(april["v1_held_without_debt_band"])
    gfc_low_months = [
        f"{row['date']} ({_num(row['v2_index'])})"
        for row in rows
        if row["window"] == "2008" and row["v2_band"] == "Low Stability"
    ]
    if gfc_v2["critical"] == 0:
        gfc_critical = "No v2 month in that window is Critical."
    else:
        gfc_critical = f"{gfc_v2['critical']} v2 months in that window are Critical."

    text = f"""# v2 candidate replay (hypothesis)

This is a research note for methodology v2.0 planning. It is not a methodology version, and it is not the live BugOut Index.

The published score stays the locked v1.0.0 formula. On the 19 September 2026 inputs that formula still returns **57.11 Moderate Stability**. Nothing in this replay is wired into `compute_index`, the weekly publisher, or `docs/data/latest.json`. Merging the branch does not publish to GitHub Pages.

Read this file. You do not need to run the harness. The month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges and band counts are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). A small chart of the same series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

v1 columns are `runtime.processing.formula.compute_index` (endpoints, weights, trust inversion, clamp, divide-by-sum-of-weights). v2 columns use `formula.normalize` and the same divide-by-sum rule on a **different basket**. Trial weights and ranges below are one hypothesis, chosen so the stress windows are visible. They are not a fitted contract.

## What the hypothesis basket is

| Trial input | Weight | Range | Direction | Where it comes from |
| --- | --- | --- | --- | --- |
| Headline CPI YoY (`CPIAUCSL`) | 0.22 | −10 to 15 | higher is less stable | Same construction as the live inflation fetcher. Endpoints are the v1.0.0 endpoints. |
| Food CPI YoY (`CPIUFDNS`) | 0.14 | 0 to 10 | higher is less stable | Same one-decimal public print as `fetch_food_shadow`. Range is the incubating draft, which the live site does not apply. |
| Labor blend | 0.28 | 70 to 83 | higher is more stable | `0.70 × LNS12300060 + 0.30 × LNS11300060`. A simple composite, not the incubating essay's unspecified participation penalty. |
| VIX monthly mean (`VIXCLS`) | 0.18 | 10 to 65 | higher is less stable | Mean of daily closes in the calendar month. The month's maximum close is stored and not scored. |
| Crime trial (RTCI) | 0.18 | 500 to 8,000 | higher is less stable | Unweighted agency mean, same construction as the crime diagnostic. v1 endpoints. Included only when that month is in the file. |

When an input is missing, its weight drops out and the denominator shrinks. The four non-crime weights sum to **0.82**. All five sum to **1.00**.

Demoted from the v2 primary, on purpose, so the side-by-side can be discussed:

- **Debt-to-GDP** is out of the primary. The sensitivity `v2_if_debt_included` adds it back at the v1 raw weight **0.12** and the v1 endpoints (0 to 200).
- **Homelessness** and **Edelman trust** are out of every v2 column. There is still no monthly history. The "if removed" columns are the locked formula with that held-constant input left out.
- **UNRATE alone** is not the v2 labor input. `v2_if_unrate` puts headline unemployment back in the labor slot (v1 range 0 to 25, weight 0.28) so the composite can be compared with the series it would replace.
- **`v2_if_epop_only`** uses prime-age EPOP alone (hypothesis range 68 to 82) instead of the 0.70/0.30 blend.
- **`v2_if_crime_held`** pins crime at the locked published input **{PUBLISHED_INCIDENT_RATE:.0f}** and labels it held constant. That pin is the 19 September 2026 baseline (`{HELD_CONSTANT_BASELINE['name']}`), not a 2008 or 2020 observation.

`v2_without_crime` is the same basket with crime always excluded. Use it when comparing 2008 (no RTCI) with later years (RTCI present).

Bands on every column are the v1.0.0 bands from `interpret`: High ≥ 70, Moderate ≥ 55, Low ≥ 40, Critical below 40. Applying those bands to a different basket is part of the hypothesis, not a retune.

## Results

{chr(10).join(summary_lines)}

Ranges are the lowest and highest scored month in that column. A blank month is not in the range. October 2025 is scored from whatever inputs exist that month, so it is inside these ranges and it is not a full-basket reading. See the recent-path section.

Band counts use the v1.0.0 thresholds on whatever number that column produced. A blank month is not counted.

{chr(10).join(band_lines)}

### Key months

{chr(10).join(key_lines)}

### Inputs behind those months

{chr(10).join(raw_lines)}

### What the windows show

**Great Recession window.** The locked partial replay (inflation, unemployment, debt only) runs {_range_phrase(gfc_v1)}. All {gfc_v1['months_scored']} months are Moderate. Held-constant crime, homelessness, and trust keep that window Moderate as well ({_range_phrase(gfc_v1_held)}). The v2 candidate runs {_range_phrase(gfc_v2)}. The low is **October 2008 at {_num(gfc_v2['min_index'])} {_short_band(by_date[str(gfc_v2['min_date'])]['v2_band'])}**, with a VIX monthly mean of {_num(by_date['2008-10-01']['v2_vix_month_mean'])}. November is the VIX-mean peak at {_num(nov_2008['v2_vix_month_mean'])} (highest daily close {_num(nov_2008['v2_vix_month_max'])}) and scores **{_num(nov_2008['v2_index'])} {_short_band(nov_2008['v2_band'])}**, a bit higher than October because headline CPI had already cooled. The Low months are {', '.join(gfc_low_months)}. October 2009, the UNRATE peak at 10.0, is v1 partial **{_num(oct_2009['v1_partial_index'])} {_short_band(oct_2009['v1_partial_band'])}** and v2 **{_num(oct_2009['v2_index'])} {_short_band(oct_2009['v2_band'])}**. This hypothesis times Great Recession stress on the volatility spike. It does not mark the later unemployment peak. There is no RTCI month in this window, so the v2 candidate and the crime-off series are the same path. {gfc_critical} None of the locked partial months leave Moderate.

**COVID window.** Locked partial runs {_range_phrase(covid_v1)}. April 2020 is **{_num(april['v1_partial_index'])} {_short_band(april['v1_partial_band'])}** partial and **{_num(april['v1_held_index'])} {_short_band(april['v1_held_band'])}** held constant (UNRATE 14.8, debt-to-GDP 132.66). Taking debt out of that held basket moves April to **{april_without_debt} {april_without_debt_band}**. Taking homelessness or trust out does not clear the Low band. Through the Great Recession window the held basket stays Moderate with or without debt, homelessness, or trust. The v2 candidate runs {_range_phrase(covid_v2)}. March 2020, the VIX monthly-mean peak at {_num(march['v2_vix_month_mean'])} (highest daily close {_num(march['v2_vix_month_max'])}), scores **{_num(march['v2_index'])} {_short_band(march['v2_band'])}** because the labor blend is still {_num(march['v2_labor_utilization'])}. April, when prime-age EPOP is {_num(april['v2_prime_age_epop'], 1)} and the blend is {_num(april['v2_labor_utilization'])}, scores **{_num(april['v2_index'])} {_short_band(april['v2_band'])}**. Replacing the blend with UNRATE that month scores **{_num(april['v2_if_unrate_index'])} {_short_band(april['v2_if_unrate_band'])}**. The trial crime rate that month is {_num(april['v2_incident_rate'])}, not {PUBLISHED_INCIDENT_RATE:.0f}. Held-constant v1 for the whole year runs {_range_phrase(covid_v1_held)}.

**Recent path.** January 2022 through August 2026. Debt is excluded on the v1 partial column before October 2025: this pull does not contain 2022–2025Q3 `GFDEGDQ188S` prints, and those months are not filled by carrying 2020 forward. The 2022 v1 partial lows are inflation plus unemployment only. June 2022 is **{_num(jun_2022['v1_partial_index'])} {_short_band(jun_2022['v1_partial_band'])}** on that two-input v1 basket, and **{_num(jun_2022['v1_held_index'])} {_short_band(jun_2022['v1_held_band'])}** once crime, homelessness, and trust are pinned at the 2026 baselines.

October 2025 is a BLS gap. CPI, food, unemployment, EPOP, and participation were non-numeric (`-(X)` or `-(9)`) and are blank. v1 partial that month is debt alone (**{_num(oct_2025['v1_partial_index'])} {_short_band(oct_2025['v1_partial_band'])}**). The v2 candidate uses only `{oct_2025['v2_inputs_present']}` (denominator {_num(oct_2025['v2_weight_denominator'])}) and prints **{_num(oct_2025['v2_index'])} {_short_band(oct_2025['v2_band'])}**. That pair is the same thin month, not a crash and not a boom. Among recent months with all five trial inputs present, the v2 candidate runs {_num(full_recent['min'])} ({full_recent['min_date']}) to {_num(full_recent['max'])} ({full_recent['max_date']}).

From October 2025 the debt print on v1 is the published 122.56815. From January 2026 it is the fixture print 122.59387, carried the way the live publisher carries a quarter. August 2026 held-constant v1 is **{_num(aug_2026['v1_held_index'])}**, the same six inputs as the locked 57.11. The v2 candidate that month is **{_num(aug_2026['v2_index'])} {_short_band(aug_2026['v2_band'])}** with crime excluded (the RTCI file ends April 2026, trial rate {_num(apr_2026['v2_incident_rate'])}). The gap versus 57.11 is the basket: debt, homelessness, and trust are out, and the labor blend and VIX are calm. It is not a claim that stability improved inside v1.0.0.

Food CPI year-over-year is above the 10% draft in {len(food_clamped)} months ({', '.join(food_clamped)}). Those months clamp the food component at 0. June 2022 food is {_num(jun_2022['v2_food_cpi_yoy'], 1)} and September 2022 is {_num(sep_2022['v2_food_cpi_yoy'], 1)}; the v2 candidate those months is {_num(jun_2022['v2_index'])} and {_num(sep_2022['v2_index'])}. The recent-window low on the v2 candidate is **{_num(recent_v2['min_index'])} on {recent_v2['min_date']}**, and that month does have the full trial basket. {len(food_deflation)} months in the three windows have negative food inflation and clamp at 100 on this draft (fully stable).

## Crime trial, and why 2008 cannot use it

The RTCI cleaned file in this pull covers **January 2018 through April 2026**. The 2008 window has no trial rate. Fair replay does not backfill those months with the locked 2723, with a later RTCI month, or with a different crime series.

The live fetcher still returns `incident_rate` **{PUBLISHED_INCIDENT_RATE:.0f}** and does not score the file. Its diagnostic month rule is the lexicographic maximum of the `Date` text, which is why a later calendar month can lose to "September". This replay uses the calendar month instead, and it does not change that lock. September 2025 in the file is a trial rate of about {_num(by_date['2025-09-01']['v2_incident_rate'])}, not 2723. Every usable month in this download has **621** agencies. That is a balanced sample, not a national census, and the rate's level is not comparable to a historical UCR series that this repo does not reconstruct.

From May 2026 through August 2026 the primary candidate excludes crime again, so the denominator changes. Compare those months with `v2_without_crime_index` before reading a jump as stress or relief.

## Debt, homelessness, trust, and UNRATE

Homelessness and trust cannot be replayed. The held-constant columns pin them at **0.23** and **41**. Removing one of them is `v1_held_without_homelessness` or `v1_held_without_trust` in the monthly CSV. That is the locked formula with one held input left out. It is not a historical path for that series.

Debt is historical inside the 2008 and 2020 windows (the locked fixture, including ordinary within-quarter carry-forward). It is not historical for most of the recent window. Adding it back onto the v2 basket only changes the score in months where a print is actually in hand.

UNRATE remains the v1 labor input. The composite is lower in April 2020 than a calm month, and it does not by itself mark October 2009 as the Great Recession trough. `v2_if_unrate` and `v2_if_epop_only` are in the CSV for that comparison. The blend and the EPOP-only range are hypotheses that bracket this sample. They are not estimated endpoints.

## What still blocks a v2.0 contract

- These weights and ranges are one labeled hypothesis. They were not fit to a loss, a utility function, or a decision threshold.
- Housing payment stress is not in the replay. No mortgage, rent-burden, or housing-delinquency series is fetched.
- Credit spreads are not in the replay. VIX is an equity-volatility index, not a credit spread. Card delinquency (`DRCCLACBS`, issue #48) is still outside the score and is not in this basket.
- The labor composite is not the incubating participation penalty. That penalty still has no formula.
- The food draft range 0–10 clamps deflation to "fully stable" and clamps the 2022 peak to "fully unstable".
- Crime has no fair 2008 path from RTCI. The published input remains locked at 2723. Agency coverage and the 12-month RTCI definition are not a national historical crime rate.
- Homelessness and Edelman trust still have no monthly history.
- Debt-to-GDP for 2022 through 2025Q3 was not in the locked fixture, and the FRED graph download did not return a body on this pull. Those months stay excluded rather than invented.
- The pull is a current revised vintage (BLS / CBOE / RTCI on {DATA_PULL_DATE}; v1 crisis fixture {FIXTURE_DOWNLOAD_DATE}). It is not ALFRED. A 2008 row is not the print available during 2008.
- Real-time vintage choice, population-adjusted crime, and a published methodology version are still open. This note does not close them.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.v2_candidate --check-locked
```

That reprints the locked 57.11 line and rewrites the CSV, this note, and the chart under `runtime/backtest/output/` and `runtime/backtest/V2_CANDIDATE.md`. It does not run the weekly publisher.

`python -m runtime.backtest` is still the v1.0.0-only replay from pull #83. The v2 command does not replace it.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
"""
    return text


def render_svg(rows: Sequence[Mapping[str, object]]) -> str:
    """Three small line charts. Not a publication graphic."""
    width = 760
    height = 220
    left = 48
    right = 16
    top = 28
    bottom = 36
    colors = {
        "v1_partial_index": "#5c6b7a",
        "v1_held_index": "#1d4e89",
        "v2_index": "#b45309",
        "v2_without_crime_index": "#0f766e",
    }
    panels = []
    for index, window_name in enumerate(V2_WINDOW_ORDER):
        subset = _window_rows(rows, window_name)
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

        def xy(i: int, value: float) -> tuple[float, float]:
            x = left + (plot_w * i / max(len(subset) - 1, 1))
            y = y0 + top + (hi - value) / (hi - lo) * plot_h
            return x, y

        lines = []
        for key, color in colors.items():
            points = []
            for i, row in enumerate(subset):
                if row[key] is None:
                    if points:
                        lines.append((color, points, key == "v2_without_crime_index"))
                        points = []
                    continue
                points.append(xy(i, float(row[key])))
            if points:
                lines.append((color, points, key == "v2_without_crime_index"))
        path_markup = []
        for color, points, dashed in lines:
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            path_markup.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="1.6"{dash} points="{coords}"/>'
            )
        title = {
            "2008": "2008 window",
            "2020": "2020 window",
            "recent": "Recent window",
        }[window_name]
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
        f'<text x="{left}" y="{len(V2_WINDOW_ORDER) * height - 4}" font-size="11" font-family="sans-serif">'
        '<tspan fill="#5c6b7a">v1 partial</tspan>'
        '<tspan fill="#1d4e89">   v1 held</tspan>'
        '<tspan fill="#b45309">   v2 candidate</tspan>'
        '<tspan fill="#0f766e">   v2 crime off</tspan>'
        "</text>"
    )
    body = "".join(panels) + legend
    total_h = len(V2_WINDOW_ORDER) * height
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" '
        f'viewBox="0 0 {width} {total_h}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>'
        f"{body}</svg>\n"
    )


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    rows = build_v2_rows()
    summary = summarize(rows)
    monthly = output_dir / MONTHLY_NAME
    summary_path = output_dir / SUMMARY_NAME
    chart_path = output_dir / CHART_NAME
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    write_monthly(rows, monthly)
    write_summary(summary, summary_path)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_text(render_svg(rows), encoding="utf-8")
    note.write_text(render_markdown(rows, summary), encoding="utf-8")
    return [monthly, summary_path, chart_path, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.v2_candidate",
        description=(
            "Score a labeled v2 candidate hypothesis beside the locked v1.0.0 "
            "replay. Does not publish the weekly score."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for the monthly CSV, summary CSV, and chart",
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
    for path in write_outputs(args.output, args.note):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
