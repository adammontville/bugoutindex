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
from runtime.processing.formula import WEIGHTS, compute_index, interpret, normalize

HYPOTHESIS_ID = "h2"
CANDIDATE_LABEL = "v2_candidate_hypothesis_h2"
DATA_PULL_DATE = "2026-09-26"
# BLS cells for this month were non-numeric in the 2026-09-26 pull.
BLS_GAP_MONTH = "2025-10-01"

# Hypothesis h2 weights. They sum to 1.00 when every trial input is present.
# They are not formula.WEIGHTS and they are not a fitted contract.
# h1 was CPI 0.22, food 0.14, labor 0.28, VIX 0.18, crime 0.18.
TRIAL_WEIGHTS = {
    "inflation_rate": 0.20,
    "food_cpi_yoy": 0.14,
    "labor_utilization": 0.30,
    "vix_month_mean": 0.16,
    "incident_rate": 0.20,
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
    # h1 food range was 0 to 10. h2 is −2 to 15.
    "food_cpi_yoy": (-2.0, 15.0),
    # h1 labor blend range was 70 to 83. h2 is 72 to 82.
    "labor_utilization": (72.0, 82.0),
    "prime_age_epop": (68.0, 82.0),
    "vix_month_mean": (10.0, 65.0),
    "incident_rate": (500.0, 8000.0),
    "unemployment_rate": (0.0, 25.0),
    "debt_to_gdp_ratio": (0.0, 200.0),
    # Side-column hypotheses. Sample in this pull: housing 1.41–11.48,
    # card delinquency 1.53–6.77. The ranges leave those peaks short of a
    # hard floor and the troughs short of fully stable.
    "housing_delinquency": (1.0, 12.0),
    "consumer_credit_delinquency": (1.0, 8.0),
    # ACS 1-year 30%+ rent burden in this pull runs 48.4 (2019) to 53.4
    # (2011). 40 to 60 leaves that trough short of fully stable and that
    # peak short of a hard floor. It is not fitted to the August band.
    "rent_burden_30": (40.0, 60.0),
    # CUUR0000SEHA 12-month change in this pull runs about −0.1 to 8.8.
    # −2 to 12 is the same kind of hypothesis range, not a burden share.
    "rent_cpi_yoy": (-2.0, 12.0),
    # Monthly-mean DGS10 from 2003 through August 2026 runs about 0.62 to
    # 5.11. 0 to 6 leaves that trough short of fully stable and that peak
    # short of a hard floor. The 1962–2026 peak near 15 is a different era.
    "treasury_10y": (0.0, 6.0),
    # DFII10 monthly means in the same file run about −1.07 to 2.89.
    "real_yield_10y": (-2.0, 4.0),
    # v1.0.0 endpoints, reused only by the "kept" sensitivity.
    "homelessness_rate": (0.0, 0.5),
    "trust_in_government": (0.0, 80.0),
}
INVERSE = frozenset({"labor_utilization", "prime_age_epop", "trust_in_government"})
LABOR_EPOP_WEIGHT = 0.70
LABOR_LFPR_WEIGHT = 0.30
DEBT_SENSITIVITY_WEIGHT = 0.12
# Side columns only. They are not in TRIAL_WEIGHTS and not in the h2 primary.
HOUSING_STRESS_WEIGHT = 0.12
CONSUMER_CREDIT_WEIGHT = 0.12
# Side columns only. Rent burden is the ACS income-share series.
# Rent CPI is a labeled shelter-inflation proxy, not that share.
RENT_BURDEN_WEIGHT = 0.12
RENT_CPI_PROXY_WEIGHT = 0.12
RENT_DATA_PULL_DATE = "2026-09-27"
# Side columns only. Nominal and real 10-year yields, not corporate OAS.
TREASURY_10Y_WEIGHT = 0.12
REAL_YIELD_WEIGHT = 0.12
RATES_DATA_PULL_DATE = "2026-09-27"
# v1.0.0 weights for the "if debt, HUD, and Edelman stayed" sensitivity.
HUD_KEPT_WEIGHT = WEIGHTS["homelessness_rate"]
TRUST_KEPT_WEIGHT = WEIGHTS["trust_in_government"]
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
    "Hypothesis h2 replay for methodology v2.0 planning. Trial weights and "
    "ranges are not a contract. v1 columns are compute_index (methodology "
    "1.0.0). v2 columns are not the published BugOut Index and are not "
    "inputs to the weekly job. h1 was the prior labeled basket "
    "(food 0–10, labor 70–83, weights 0.22/0.14/0.28/0.18/0.18)."
)

SUMMARY_SCENARIOS = (
    ("v1_partial", "v1.0.0 partial (crime, homelessness, trust excluded)"),
    ("v1_held", "v1.0.0 held constant (2723 / 0.23 / 41)"),
    ("v1_held_without_debt", "v1.0.0 held, debt removed"),
    ("v1_held_without_homelessness", "v1.0.0 held, homelessness removed"),
    ("v1_held_without_trust", "v1.0.0 held, trust removed"),
    ("v1_partial_without_debt", "v1.0.0 partial, debt also removed"),
    ("v2", "v2 candidate h2 (crime trial when the RTCI month exists)"),
    ("v2_without_crime", "v2 candidate h2 with crime always excluded"),
    ("v2_if_unrate", "v2 h2 basket with UNRATE instead of the labor composite"),
    ("v2_if_epop_only", "v2 h2 basket with prime-age EPOP instead of the composite"),
    ("v2_if_debt_included", "v2 h2 basket plus debt-to-GDP at weight 0.12"),
    ("v2_if_crime_held", "v2 h2 basket with crime held at the locked 2723"),
    ("v2_if_housing", "v2 h2 basket plus mortgage delinquency at weight 0.12"),
    (
        "v2_if_consumer_credit",
        "v2 h2 basket plus credit-card delinquency at weight 0.12",
    ),
    (
        "v2_if_housing_and_consumer",
        "v2 h2 basket plus mortgage and credit-card delinquency",
    ),
    (
        "v2_if_rent_burden",
        "v2 h2 basket plus ACS 30% rent burden at weight 0.12",
    ),
    (
        "v2_if_rent_burden_and_consumer",
        "v2 h2 basket plus ACS 30% rent burden and credit-card delinquency",
    ),
    (
        "v2_if_rent_cpi_proxy",
        "v2 h2 basket plus rent-of-primary-residence CPI YoY (proxy, not burden)",
    ),
    ("v2_if_dgs10", "v2 h2 basket plus 10-year Treasury yield at weight 0.12"),
    ("v2_if_real_yield", "v2 h2 basket plus 10-year real yield at weight 0.12"),
    (
        "v2_if_rates",
        "v2 h2 basket plus 10-year nominal and real yields",
    ),
    (
        "v2_if_kept_debt_hud_trust",
        "v2 h2 basket plus debt when present and the HUD and Edelman pins",
    ),
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
    ("2022-06-01", "Food CPI year-over-year 10.4 (inside h2; a hard floor under h1)"),
    ("2022-09-01", "Food CPI year-over-year high in this pull"),
    ("2025-10-01", "BLS publication gap in this pull"),
    ("2026-04-01", "Last month in the RTCI trial file"),
    ("2026-08-01", "Latest headline CPI month; locked-score inputs"),
)

# Prior committed h1 replay. These numbers are not recomputed by this command.
# They are the scores from the first labeled basket so a reader can compare
# h2 with h1 without a local run. h1 food range was 0–10, labor range 70–83,
# weights CPI 0.22 / food 0.14 / labor 0.28 / VIX 0.18 / crime 0.18.
H1_KEY_SCORES = {
    "2008-10-01": {"v2": (45.62, "Low"), "crime_off": (45.62, "Low")},
    "2009-10-01": {"v2": (68.72, "Moderate"), "crime_off": (68.72, "Moderate")},
    "2020-03-01": {"v2": (60.58, "Moderate"), "crime_off": (58.28, "Moderate")},
    "2020-04-01": {"v2": (48.32, "Low"), "crime_off": (43.24, "Low")},
    "2022-06-01": {"v2": (52.87, "Low"), "crime_off": (48.85, "Low")},
    "2026-08-01": {"v2": (74.51, "High"), "crime_off": (74.51, "High")},
}
H1_COMPARE_MONTHS = (
    "2008-10-01",
    "2009-10-01",
    "2020-03-01",
    "2020-04-01",
    "2022-06-01",
    "2026-08-01",
)
HOUSEHOLD_COMPARE_MONTHS = (
    "2008-10-01",
    "2009-10-01",
    "2020-04-01",
    "2022-06-01",
    "2026-08-01",
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


def _load_rent_burden(path: Path) -> tuple[dict[str, float], dict[str, float]]:
    """ACS 1-year 30%+ share (scored) and 50%+ share (diagnostic only)."""
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
    crime = {}
    with (folder / "RTCI_monthly.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            crime[row["observation_date"]] = {
                "unweighted": float(row["incident_rate_unweighted"]),
                "population_weighted": float(row["incident_rate_population_weighted"]),
                "agencies": int(row["agencies"]),
            }
    extra_debt = _as_float_map(_load_text_series(folder / "GFDEGDQ188S_published_extra.csv"))
    rent_30, rent_50 = _load_rent_burden(folder / "B25070.csv")
    return {
        "cpi": _load_text_series(folder / "CPIAUCSL.csv"),
        "food": _load_text_series(folder / "CPIUFDNS.csv"),
        "epop": _as_float_map(_load_text_series(folder / "LNS12300060.csv")),
        "lfpr": _as_float_map(_load_text_series(folder / "LNS11300060.csv")),
        "unrate": _as_float_map(_load_text_series(folder / "LNS14000000.csv")),
        "vix": vix_rows,
        "crime": crime,
        "extra_debt": extra_debt,
        "housing_delinquency": _as_float_map(_load_text_series(folder / "DRSFRMACBS.csv")),
        "consumer_credit_delinquency": _as_float_map(
            _load_text_series(folder / "DRCCLACBS.csv")
        ),
        "rent_burden_30": rent_30,
        "rent_burden_50": rent_50,
        "rent_cpi": _load_text_series(folder / "CUUR0000SEHA.csv"),
        "treasury_10y": _as_float_map(_load_text_series(folder / "DGS10_monthly.csv")),
        "real_yield_10y": _as_float_map(_load_text_series(folder / "DFII10_monthly.csv")),
    }


def quarterly_asof(series: Mapping[str, float], day: str) -> tuple[Optional[float], str, str]:
    """Latest quarterly print on or before ``day``.

    Same rule as the debt column: the quarter-start month is ``observed``.
    Later months keep that print as ``carried_forward``. A month before the
    first print is ``excluded``. This is not an interpolation.
    """
    available = [stamp for stamp in series if stamp <= day]
    if not available:
        return None, "excluded", ""
    chosen = max(available)
    status = "observed" if chosen == day else "carried_forward"
    return series[chosen], status, chosen


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
        elif name == "housing_delinquency":
            weights[name] = HOUSING_STRESS_WEIGHT
        elif name == "consumer_credit_delinquency":
            weights[name] = CONSUMER_CREDIT_WEIGHT
        elif name == "rent_burden_30":
            weights[name] = RENT_BURDEN_WEIGHT
        elif name == "rent_cpi_yoy":
            weights[name] = RENT_CPI_PROXY_WEIGHT
        elif name == "treasury_10y":
            weights[name] = TREASURY_10Y_WEIGHT
        elif name == "real_yield_10y":
            weights[name] = REAL_YIELD_WEIGHT
        elif name == "homelessness_rate":
            weights[name] = HUD_KEPT_WEIGHT
        elif name == "trust_in_government":
            weights[name] = TRUST_KEPT_WEIGHT
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
            housing_raw, housing_status, housing_date = quarterly_asof(
                bundle["housing_delinquency"], day
            )
            credit_raw, credit_status, credit_date = quarterly_asof(
                bundle["consumer_credit_delinquency"], day
            )
            parts["housing_delinquency"] = housing_raw
            parts["consumer_credit_delinquency"] = credit_raw
            housing_order = PRIMARY_ORDER + ("housing_delinquency",)
            credit_order = PRIMARY_ORDER + ("consumer_credit_delinquency",)
            both_order = PRIMARY_ORDER + (
                "housing_delinquency",
                "consumer_credit_delinquency",
            )
            if_housing = score_basket(parts, housing_order, _weights_for(housing_order))
            if_credit = score_basket(parts, credit_order, _weights_for(credit_order))
            if_both = score_basket(parts, both_order, _weights_for(both_order))
            rent_raw, rent_status, rent_date = quarterly_asof(bundle["rent_burden_30"], day)
            rent50_raw, _rent50_status, _rent50_date = quarterly_asof(
                bundle["rent_burden_50"], day
            )
            rent_cpi = _inflation_from_texts(bundle["rent_cpi"], day)
            rent_cpi_status = "observed" if rent_cpi is not None else "excluded"
            parts["rent_burden_30"] = rent_raw
            parts["rent_cpi_yoy"] = rent_cpi
            rent_order = PRIMARY_ORDER + ("rent_burden_30",)
            rent_credit_order = PRIMARY_ORDER + (
                "rent_burden_30",
                "consumer_credit_delinquency",
            )
            proxy_order = PRIMARY_ORDER + ("rent_cpi_yoy",)
            if_rent = score_basket(parts, rent_order, _weights_for(rent_order))
            if_rent_credit = score_basket(
                parts, rent_credit_order, _weights_for(rent_credit_order)
            )
            if_rent_proxy = score_basket(parts, proxy_order, _weights_for(proxy_order))
            treasury_raw = bundle["treasury_10y"].get(day)
            real_raw = bundle["real_yield_10y"].get(day)
            treasury_status = "observed" if treasury_raw is not None else "excluded"
            real_status = "observed" if real_raw is not None else "excluded"
            parts["treasury_10y"] = treasury_raw
            parts["real_yield_10y"] = real_raw
            dgs_order = PRIMARY_ORDER + ("treasury_10y",)
            real_order = PRIMARY_ORDER + ("real_yield_10y",)
            rates_order = PRIMARY_ORDER + ("treasury_10y", "real_yield_10y")
            if_dgs = score_basket(parts, dgs_order, _weights_for(dgs_order))
            if_real = score_basket(parts, real_order, _weights_for(real_order))
            if_rates = score_basket(parts, rates_order, _weights_for(rates_order))
            kept_values = dict(parts)
            kept_values["debt_to_gdp_ratio"] = debt_raw
            kept_values["homelessness_rate"] = float(HELD_CONSTANT_BASELINE["homelessness_rate"])
            kept_values["trust_in_government"] = float(HELD_CONSTANT_BASELINE["trust_in_government"])
            kept_order = PRIMARY_ORDER + (
                "debt_to_gdp_ratio",
                "homelessness_rate",
                "trust_in_government",
            )
            if_kept = score_basket(kept_values, kept_order, _weights_for(kept_order))
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
                    "v2_housing_delinquency": housing_raw,
                    "v2_housing_status": housing_status,
                    "v2_housing_observation_date": housing_date,
                    "v2_if_housing_index": if_housing["index"],
                    "v2_if_housing_band": if_housing["band"],
                    "v2_consumer_credit_delinquency": credit_raw,
                    "v2_consumer_credit_status": credit_status,
                    "v2_consumer_credit_observation_date": credit_date,
                    "v2_if_consumer_credit_index": if_credit["index"],
                    "v2_if_consumer_credit_band": if_credit["band"],
                    "v2_if_housing_and_consumer_index": if_both["index"],
                    "v2_if_housing_and_consumer_band": if_both["band"],
                    "v2_rent_burden_30": rent_raw,
                    "v2_rent_burden_status": rent_status,
                    "v2_rent_burden_observation_date": rent_date,
                    "v2_rent_burden_50": rent50_raw,
                    "v2_if_rent_burden_index": if_rent["index"],
                    "v2_if_rent_burden_band": if_rent["band"],
                    "v2_if_rent_burden_and_consumer_index": if_rent_credit["index"],
                    "v2_if_rent_burden_and_consumer_band": if_rent_credit["band"],
                    "v2_rent_cpi_yoy": rent_cpi,
                    "v2_rent_cpi_status": rent_cpi_status,
                    "v2_if_rent_cpi_proxy_index": if_rent_proxy["index"],
                    "v2_if_rent_cpi_proxy_band": if_rent_proxy["band"],
                    "v2_treasury_10y": treasury_raw,
                    "v2_treasury_10y_status": treasury_status,
                    "v2_if_dgs10_index": if_dgs["index"],
                    "v2_if_dgs10_band": if_dgs["band"],
                    "v2_real_yield_10y": real_raw,
                    "v2_real_yield_status": real_status,
                    "v2_if_real_yield_index": if_real["index"],
                    "v2_if_real_yield_band": if_real["band"],
                    "v2_if_rates_index": if_rates["index"],
                    "v2_if_rates_band": if_rates["band"],
                    "v2_if_kept_debt_hud_trust_index": if_kept["index"],
                    "v2_if_kept_debt_hud_trust_band": if_kept["band"],
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
    "v2_housing_delinquency",
    "v2_housing_status",
    "v2_housing_observation_date",
    "v2_if_housing_index",
    "v2_if_housing_band",
    "v2_consumer_credit_delinquency",
    "v2_consumer_credit_status",
    "v2_consumer_credit_observation_date",
    "v2_if_consumer_credit_index",
    "v2_if_consumer_credit_band",
    "v2_if_housing_and_consumer_index",
    "v2_if_housing_and_consumer_band",
    "v2_rent_burden_30",
    "v2_rent_burden_status",
    "v2_rent_burden_observation_date",
    "v2_rent_burden_50",
    "v2_if_rent_burden_index",
    "v2_if_rent_burden_band",
    "v2_if_rent_burden_and_consumer_index",
    "v2_if_rent_burden_and_consumer_band",
    "v2_rent_cpi_yoy",
    "v2_rent_cpi_status",
    "v2_if_rent_cpi_proxy_index",
    "v2_if_rent_cpi_proxy_band",
    "v2_treasury_10y",
    "v2_treasury_10y_status",
    "v2_if_dgs10_index",
    "v2_if_dgs10_band",
    "v2_real_yield_10y",
    "v2_real_yield_status",
    "v2_if_real_yield_index",
    "v2_if_real_yield_band",
    "v2_if_rates_index",
    "v2_if_rates_band",
    "v2_if_kept_debt_hud_trust_index",
    "v2_if_kept_debt_hud_trust_band",
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
    "v2_if_housing_index",
    "v2_if_consumer_credit_index",
    "v2_if_housing_and_consumer_index",
    "v2_if_rent_burden_index",
    "v2_if_rent_burden_and_consumer_index",
    "v2_if_rent_cpi_proxy_index",
    "v2_if_dgs10_index",
    "v2_if_real_yield_index",
    "v2_if_rates_index",
    "v2_if_kept_debt_hud_trust_index",
}
_ONE_DECIMAL = {"v2_food_cpi_yoy", "v2_rent_burden_30", "v2_rent_burden_50"}
_TWO_DECIMAL = {
    "v2_labor_utilization",
    "v2_vix_month_mean",
    "v2_vix_month_max",
    "v2_incident_rate",
    "v2_incident_population_weighted",
    "v2_housing_delinquency",
    "v2_consumer_credit_delinquency",
    "v2_rent_cpi_yoy",
    "v2_treasury_10y",
    "v2_real_yield_10y",
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
        "v2_if_housing": "v2_if_housing_index",
        "v2_if_consumer_credit": "v2_if_consumer_credit_index",
        "v2_if_housing_and_consumer": "v2_if_housing_and_consumer_index",
        "v2_if_rent_burden": "v2_if_rent_burden_index",
        "v2_if_rent_burden_and_consumer": "v2_if_rent_burden_and_consumer_index",
        "v2_if_rent_cpi_proxy": "v2_if_rent_cpi_proxy_index",
        "v2_if_dgs10": "v2_if_dgs10_index",
        "v2_if_real_yield": "v2_if_real_yield_index",
        "v2_if_rates": "v2_if_rates_index",
        "v2_if_kept_debt_hud_trust": "v2_if_kept_debt_hud_trust_index",
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


def _signed(value: float) -> str:
    """Plain range endpoint, with a minus sign for negatives."""
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
    food_lo, food_hi = TRIAL_RANGES["food_cpi_yoy"]
    food_above_range = [
        str(row["date"])
        for row in rows
        if row["v2_food_cpi_yoy"] is not None and float(row["v2_food_cpi_yoy"]) > food_hi
    ]
    food_below_range = [
        str(row["date"])
        for row in rows
        if row["v2_food_cpi_yoy"] is not None and float(row["v2_food_cpi_yoy"]) < food_lo
    ]
    food_above_h1_floor = [
        str(row["date"])
        for row in rows
        if row["v2_food_cpi_yoy"] is not None and float(row["v2_food_cpi_yoy"]) > 10
    ]
    food_mild_negative = [
        str(row["date"])
        for row in rows
        if row["v2_food_cpi_yoy"] is not None
        and food_lo <= float(row["v2_food_cpi_yoy"]) < 0
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
        "| Month | Why it is here | v1 held | h2 | h2, crime off | h2 + housing | h2 + consumer credit | h2 + both | v2, UNRATE instead | v2, debt added |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day, reason in KEY_MONTHS:
        row = by_date[day]
        key_lines.append(
            "| {day} | {reason} | {h} | {v} | {c} | {hs} | {cc} | {both} | {u} | {d} |".format(
                day=day,
                reason=reason,
                h=cell(row, "v1_held_index"),
                v=cell(row, "v2_index"),
                c=cell(row, "v2_without_crime_index"),
                hs=cell(row, "v2_if_housing_index"),
                cc=cell(row, "v2_if_consumer_credit_index"),
                both=cell(row, "v2_if_housing_and_consumer_index"),
                u=cell(row, "v2_if_unrate_index"),
                d=cell(row, "v2_if_debt_included_index"),
            )
        )
    household_lines = [
        "| Month | Mortgage % | Mortgage as-of | Card % | Card as-of | h2 | + housing | + consumer | + both |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day in HOUSEHOLD_COMPARE_MONTHS:
        row = by_date[day]
        household_lines.append(
            "| {day} | {hv} | {hs} | {cv} | {cs} | {v} | {vh} | {vc} | {vb} |".format(
                day=day,
                hv=_num(row["v2_housing_delinquency"]),
                hs=f"{row['v2_housing_observation_date']} {row['v2_housing_status']}",
                cv=_num(row["v2_consumer_credit_delinquency"]),
                cs=(
                    f"{row['v2_consumer_credit_observation_date']} "
                    f"{row['v2_consumer_credit_status']}"
                ),
                v=cell(row, "v2_index"),
                vh=cell(row, "v2_if_housing_index"),
                vc=cell(row, "v2_if_consumer_credit_index"),
                vb=cell(row, "v2_if_housing_and_consumer_index"),
            )
        )
    rent_lines = [
        "| Month | 30%+ | 50%+ (not scored) | Burden as-of | h2 | + rent burden | + burden and cards | Rent CPI YoY | + rent CPI proxy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for day in HOUSEHOLD_COMPARE_MONTHS:
        row = by_date[day]
        rent_lines.append(
            "| {day} | {p30} | {p50} | {asof} | {v} | {rb} | {both} | {yoy} | {proxy} |".format(
                day=day,
                p30=_num(row["v2_rent_burden_30"], 1),
                p50=_num(row["v2_rent_burden_50"], 1),
                asof=(
                    f"{row['v2_rent_burden_observation_date']} "
                    f"{row['v2_rent_burden_status']}"
                ),
                v=cell(row, "v2_index"),
                rb=cell(row, "v2_if_rent_burden_index"),
                both=cell(row, "v2_if_rent_burden_and_consumer_index"),
                yoy=_num(row["v2_rent_cpi_yoy"]),
                proxy=cell(row, "v2_if_rent_cpi_proxy_index"),
            )
        )
    # Full ACS file, not only the years a replay window happens to carry.
    annual_burden = load_v2_bundle()["rent_burden_30"]
    burden_low_year = min(annual_burden, key=lambda stamp: (annual_burden[stamp], stamp))
    burden_high_year = max(annual_burden, key=lambda stamp: (annual_burden[stamp], stamp))
    proxy_values = [
        (str(row["date"]), float(row["v2_rent_cpi_yoy"]))
        for row in rows
        if row["v2_rent_cpi_yoy"] is not None
    ]
    proxy_peak_day, proxy_peak = max(proxy_values, key=lambda item: (item[1], item[0]))
    rent_lo, rent_hi = TRIAL_RANGES["rent_burden_30"]
    proxy_lo, proxy_hi = TRIAL_RANGES["rent_cpi_yoy"]
    rate_lines = [
        "| Month | 10y % | Real 10y % | h2 | + 10y | + real yield | + both rates |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    kept_lines = [
        "| Month | h2 | Debt status | h2 + debt | h2 + debt, HUD pin, Edelman pin | v1 held |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for day in HOUSEHOLD_COMPARE_MONTHS:
        row = by_date[day]
        rate_lines.append(
            "| {day} | {y10} | {real} | {v} | {dgs} | {ry} | {both} |".format(
                day=day,
                y10=_num(row["v2_treasury_10y"]),
                real=_num(row["v2_real_yield_10y"]),
                v=cell(row, "v2_index"),
                dgs=cell(row, "v2_if_dgs10_index"),
                ry=cell(row, "v2_if_real_yield_index"),
                both=cell(row, "v2_if_rates_index"),
            )
        )
        kept_lines.append(
            "| {day} | {v} | {debt} | {plus} | {kept} | {held} |".format(
                day=day,
                v=cell(row, "v2_index"),
                debt=str(row["v1_debt_status"]),
                plus=cell(row, "v2_if_debt_included_index"),
                kept=cell(row, "v2_if_kept_debt_hud_trust_index"),
                held=cell(row, "v1_held_index"),
            )
        )
    treasury_sample = load_v2_bundle()["treasury_10y"]
    real_sample = load_v2_bundle()["real_yield_10y"]
    treasury_low = min(treasury_sample, key=lambda stamp: (treasury_sample[stamp], stamp))
    treasury_high = max(treasury_sample, key=lambda stamp: (treasury_sample[stamp], stamp))
    real_low = min(real_sample, key=lambda stamp: (real_sample[stamp], stamp))
    real_high = max(real_sample, key=lambda stamp: (real_sample[stamp], stamp))
    y10_lo, y10_hi = TRIAL_RANGES["treasury_10y"]
    real_lo_end, real_hi_end = TRIAL_RANGES["real_yield_10y"]
    aug_rates = float(aug_2026["v2_if_rates_index"])
    aug_dgs = float(aug_2026["v2_if_dgs10_index"])
    if aug_dgs >= 70 and aug_rates >= 55 and aug_rates < 70:
        rates_read = (
            "The 10-year level alone leaves August in High. Nominal and real yields "
            "together put August in Moderate. That combined column gives long yields "
            "two side-column weights (0.24). Read the 10-year column first."
        )
    elif aug_dgs >= 70 and aug_rates >= 70:
        rates_read = "August stays High with the 10-year alone and with both yield series."
    elif aug_dgs < 70:
        rates_read = (
            "The 10-year level alone moves August out of High. "
            "That is the financing-cost column."
        )
    else:
        rates_read = "See the table for the August bands."

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

    non_crime_weight = sum(
        weight for name, weight in TRIAL_WEIGHTS.items() if name != "incident_rate"
    )
    food_lo_txt = _signed(food_lo)
    food_hi_txt = _signed(food_hi)
    labor_lo, labor_hi = TRIAL_RANGES["labor_utilization"]
    oct_2008 = by_date["2008-10-01"]
    gap_h1 = 68.72 - 45.62
    gap_h2 = float(oct_2009["v2_index"]) - float(oct_2008["v2_index"])
    if gap_h2 < gap_h1 - 0.05:
        gap_read = (
            f"October 2009 moved closer to October 2008 "
            f"({gap_h2:.2f} points apart, versus {gap_h1:.2f} under h1)."
        )
        if (
            float(oct_2009["v2_index"]) > float(oct_2008["v2_index"])
            and oct_2009["v2_band"] == "Moderate Stability"
        ):
            gap_read += (
                " It is still Moderate, and October 2008 is still the lower score. "
                "The tighter labor band did not make late 2009 the window's trough."
            )
    elif gap_h2 > gap_h1 + 0.05:
        gap_read = (
            f"October 2009 moved farther from October 2008 "
            f"({gap_h2:.2f} points apart, versus {gap_h1:.2f} under h1)."
        )
    else:
        gap_read = (
            f"The gap between October 2009 and October 2008 is about the same as under h1 "
            f"({gap_h2:.2f} points, versus {gap_h1:.2f})."
        )
    june_h1 = H1_KEY_SCORES["2022-06-01"]["v2"][0]
    june_h2 = float(jun_2022["v2_index"])
    if june_h2 > june_h1 + 0.05:
        food_move = (
            f"June 2022 moves from h1 **{june_h1:.2f}** to h2 **{_num(jun_2022['v2_index'])}**. "
            "That is less stressed than h1's hard floor on food, which is what the wider range was for."
        )
    elif june_h2 < june_h1 - 0.05:
        food_move = (
            f"June 2022 moves from h1 **{june_h1:.2f}** to h2 **{_num(jun_2022['v2_index'])}**, "
            "more stressed than h1 even with the wider food range."
        )
    else:
        food_move = (
            f"June 2022 is **{_num(jun_2022['v2_index'])}**, about the same as h1 **{june_h1:.2f}**."
        )
    if food_above_range:
        food_above_sentence = (
            f"{len(food_above_range)} months are above {food_hi_txt} and clamp the food component at 0 "
            f"({', '.join(food_above_range)})."
        )
    else:
        food_above_sentence = (
            f"No month in these windows has food inflation above {food_hi_txt}, so the food "
            "component does not hit the fully-unstable clamp."
        )
    if food_below_range:
        food_below_sentence = (
            f"{len(food_below_range)} months are below {food_lo_txt} and clamp the food component at 100 "
            f"({', '.join(food_below_range)})."
        )
    else:
        food_below_sentence = (
            f"No month in these windows has food inflation below {food_lo_txt}, so the food "
            "component does not hit the fully-stable clamp."
        )
    h1_compare_lines = [
        "| Month | h1 v2 | h1, crime off | h2 v2 | h2, crime off | v1 held |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for day in H1_COMPARE_MONTHS:
        prior = H1_KEY_SCORES[day]
        row = by_date[day]
        h1_compare_lines.append(
            "| {day} | {hv} {hvb} | {hc} {hcb} | {v} | {c} | {held} |".format(
                day=day,
                hv=f"{prior['v2'][0]:.2f}",
                hvb=prior["v2"][1],
                hc=f"{prior['crime_off'][0]:.2f}",
                hcb=prior["crime_off"][1],
                v=cell(row, "v2_index"),
                c=cell(row, "v2_without_crime_index"),
                held=cell(row, "v1_held_index"),
            )
        )

    text = f"""# v2 candidate replay (hypothesis h2)

This is a research note for methodology v2.0 planning. It is not a methodology version, and it is not the live BugOut Index. The tables below are **hypothesis h2**. Hypothesis h1 was the previous labeled basket on this branch: food CPI year-over-year range 0 to 10, labor blend range 70 to 83, and weights CPI 0.22, food 0.14, labor 0.28, VIX 0.18, crime 0.18. h1 is not recomputed here. Its six comparison months are copied from that earlier replay so the two baskets can be read side by side.

The published score stays the locked v1.0.0 formula. On the 19 September 2026 inputs that formula still returns **57.11 Moderate Stability**. Nothing in this replay is wired into `compute_index`, the weekly publisher, or `docs/data/latest.json`. Merging the branch does not publish to GitHub Pages.

Read this file. You do not need to run the harness. The month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges and band counts are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). A small chart of the same series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

v1 columns are `runtime.processing.formula.compute_index` (endpoints, weights, trust inversion, clamp, divide-by-sum-of-weights). v2 columns use `formula.normalize` and the same divide-by-sum rule on a **different basket**. Trial weights and ranges below are hypothesis h2. They are not a fitted contract.

## What hypothesis h2 changes

| Piece | h1 | h2 (this note) | Why h2 |
| --- | --- | --- | --- |
| Food CPI YoY range | 0 to 10 | {food_lo_txt} to {food_hi_txt} | The 0–10 draft clamped nine 2022–23 months at fully unstable and treated mild food deflation as fully stable. |
| Labor blend range | 70 to 83 | {labor_lo:g} to {labor_hi:g} | October 2009 (blend about 77, UNRATE 10.0) scored too calm next to the VIX-timed October 2008 Low. A tighter band pulls that labor stress up. This is not a participation penalty. |
| CPI / food / labor / VIX / crime weights | 0.22 / 0.14 / 0.28 / 0.18 / 0.18 | {TRIAL_WEIGHTS['inflation_rate']:.2f} / {TRIAL_WEIGHTS['food_cpi_yoy']:.2f} / {TRIAL_WEIGHTS['labor_utilization']:.2f} / {TRIAL_WEIGHTS['vix_month_mean']:.2f} / {TRIAL_WEIGHTS['incident_rate']:.2f} | Nudge labor up and VIX down so the Great Recession window is less pure-VIX and the late-2009 unemployment era registers more. Crime stays in the same ballpark. |

Headline CPI endpoints, the VIX range, the crime range, the labor blend formula (`0.70 × EPOP + 0.30 × LFPR`), and the crime trial rule are unchanged. Crime is still excluded when the RTCI month is absent. 2008 is not backfilled. The published crime input stays locked at {PUBLISHED_INCIDENT_RATE:.0f}.

### h1 versus h2 on six months

h1 figures are the prior committed replay. h2 figures are this run. v1 held is the locked formula and does not change between hypotheses.

{chr(10).join(h1_compare_lines)}

## What the h2 basket is

| Trial input | Weight | Range | Direction | Where it comes from |
| --- | --- | --- | --- | --- |
| Headline CPI YoY (`CPIAUCSL`) | {TRIAL_WEIGHTS['inflation_rate']:.2f} | −10 to 15 | higher is less stable | Same construction as the live inflation fetcher. Endpoints are the v1.0.0 endpoints. Unchanged from h1. |
| Food CPI YoY (`CPIUFDNS`) | {TRIAL_WEIGHTS['food_cpi_yoy']:.2f} | {food_lo_txt} to {food_hi_txt} | higher is less stable | Same one-decimal public print as `fetch_food_shadow`. h2 range. The live site does not apply it. |
| Labor blend | {TRIAL_WEIGHTS['labor_utilization']:.2f} | {labor_lo:g} to {labor_hi:g} | higher is more stable | `0.70 × LNS12300060 + 0.30 × LNS11300060`. A simple composite, not the incubating essay's unspecified participation penalty. h2 range. |
| VIX monthly mean (`VIXCLS`) | {TRIAL_WEIGHTS['vix_month_mean']:.2f} | 10 to 65 | higher is less stable | Mean of daily closes in the calendar month. The month's maximum close is stored and not scored. Range unchanged from h1. |
| Crime trial (RTCI) | {TRIAL_WEIGHTS['incident_rate']:.2f} | 500 to 8,000 | higher is less stable | Unweighted agency mean, same construction as the crime diagnostic. v1 endpoints. Included only when that month is in the file. |

When an input is missing, its weight drops out and the denominator shrinks. The four non-crime weights sum to **{non_crime_weight:.2f}**. All five sum to **1.00**.

Demoted from the v2 primary, on purpose, so the side-by-side can be discussed:

- **Debt-to-GDP** is out of the primary. The sensitivity `v2_if_debt_included` adds it back at the v1 raw weight **0.12** and the v1 endpoints (0 to 200).
- **Mortgage delinquency** and **credit-card delinquency** are out of the primary. They are side columns (`v2_if_housing`, `v2_if_consumer_credit`, `v2_if_housing_and_consumer`) at trial weight 0.12 each. They answer a coverage question. They do not replace h2.
- **Rent burden** is out of the primary. `v2_if_rent_burden` adds the ACS 30%+ share at trial weight {RENT_BURDEN_WEIGHT:.2f}. `v2_if_rent_burden_and_consumer` adds that share and card delinquency. The 50%+ share is stored and not scored. `v2_if_rent_cpi_proxy` is rent-of-primary-residence inflation, labeled as a proxy, not as rent burden.
- **Treasury yields** are out of the primary. `v2_if_dgs10` adds the 10-year yield, `v2_if_real_yield` adds the 10-year real yield, and `v2_if_rates` adds both. Corporate credit spreads stay out.
- **`v2_if_kept_debt_hud_trust`** puts debt (when a print exists) and the locked HUD and Edelman pins back on h2 at their v1.0.0 weights. It is a replacement check before demotion. It is not a historical path for homelessness or trust, and it does not unlock crime.
- **Homelessness** and **Edelman trust** are out of every v2 column. There is still no monthly history. The "if removed" columns are the locked formula with that held-constant input left out.
- **UNRATE alone** is not the v2 labor input. `v2_if_unrate` puts headline unemployment back in the labor slot (v1 range 0 to 25, weight {TRIAL_WEIGHTS['labor_utilization']:.2f}) so the composite can be compared with the series it would replace.
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

h2 is still the primary candidate. Housing delinquency, card delinquency, rent burden, and the rent-CPI proxy are side columns for the coverage question “August 2026 High feels wrong.” They are not a new primary basket and they are not in the live score. UNRATE-instead and debt-added stay in this table; v1 partial stays in the monthly CSV. The rent-burden comparison is in the next section.

{chr(10).join(key_lines)}

### Household stress side columns

These two series are household payment difficulty, not corporate credit spreads. The public FRED graph CSV did not return a body on this pull. The levels are the Federal Reserve Board charge-off and delinquency release (CHGDEL), the release FRED uses for these series, downloaded 2026-09-26. The package observations run through 2026-06-30. Each print is stored on the quarter-start month. Later months in the harness use that print as `carried_forward`, the same rule as debt-to-GDP. A month with no print on or before it would drop the weight. None of the three windows are in that state.

| Series | FRED id | What it measures | Frequency | Trial weight | Trial range |
| --- | --- | --- | --- | --- | --- |
| Mortgage delinquency | `DRSFRMACBS` | Delinquency rate on loans secured by one- to four-family residential property, including home-equity lines, all commercial banks, seasonally adjusted, percent. Fed table column “Residential,” booked in domestic offices. | Quarterly | {HOUSING_STRESS_WEIGHT:.2f} | 1 to 12 |
| Credit-card delinquency | `DRCCLACBS` | Delinquency rate on consumer credit card loans, all commercial banks, seasonally adjusted, percent. Issue #48. Not a bond spread. | Quarterly | {CONSUMER_CREDIT_WEIGHT:.2f} | 1 to 8 |

Higher delinquency is less stable. This pull’s sample runs from 1991 Q1 through 2026 Q2: mortgage delinquency 1.41 to 11.48, card delinquency 1.53 to 6.77. The ranges leave those peaks short of a hard floor. Weight 0.12 matches the debt side column. It is a hypothesis, not a fitted share of h2.

{chr(10).join(household_lines)}

August 2026 is **{cell(aug_2026, 'v2_index')}** on h2, **{cell(aug_2026, 'v2_if_housing_index')}** with mortgage delinquency, **{cell(aug_2026, 'v2_if_consumer_credit_index')}** with card delinquency, and **{cell(aug_2026, 'v2_if_housing_and_consumer_index')}** with both. The rates that month are the 2026 Q2 prints carried forward ({_num(aug_2026['v2_housing_delinquency'])}% mortgages, {_num(aug_2026['v2_consumer_credit_delinquency'])}% cards, observation {aug_2026['v2_housing_observation_date']}). There is no 2026 Q3 print in this file. Mortgage delinquency is near the calm end of the sample, so adding it does not pull August toward Moderate. Card delinquency is above its trough and far below the 2009 peak, and the 0.12 weight does not move August out of High either.

October 2009 is where the mortgage series does the work h2’s labor blend did not. Mortgage delinquency is {_num(oct_2009['v2_housing_delinquency'])}% and card delinquency is {_num(oct_2009['v2_consumer_credit_delinquency'])}%. h2 is **{cell(oct_2009, 'v2_index')}**. With both side series it is **{cell(oct_2009, 'v2_if_housing_and_consumer_index')}**. October 2008 is already a VIX Low on h2 (**{cell(oct_2008, 'v2_index')}**); adding both household series scores **{cell(oct_2008, 'v2_if_housing_and_consumer_index')}**.

April 2020 is the opposite case. Bank delinquency was low while prime-age employment had already broken, which is what forbearance does to this series. h2 is **{cell(april, 'v2_index')}**. With both household series it is **{cell(april, 'v2_if_housing_and_consumer_index')}**. These columns do not mark the COVID labor trough.

### Rent burden side column

There is no monthly national rent-burden series. Rent burden here is the share of renter households whose gross rent is at least 30% of household income, the Census cost-burden convention. It is not mortgage delinquency (`DRSFRMACBS`) and it is not corporate credit.

The source is ACS table **B25070**, Gross Rent as a Percentage of Household Income in the Past 12 Months, national 1-year estimates. The scored share is `(30–34.9% + 35–39.9% + 40–49.9% + 50% or more) / (total − not computed) × 100`, rounded half-up to one decimal. “Not computed” stays out of the denominator. The **50%+** share uses the same denominator and is the severe-burden convention. It is a subset of the 30% group, so it is stored on the row and not given a second weight.

| Piece | Choice |
| --- | --- |
| Series | `B25070` national 1-year. 2007–2009 from the ACS summary file (sequences 134, 138, and 148; United States logrecno 1). 2010–2019 and 2021–2024 from `data.census.gov` product `ACSDT1Y{{year}}.B25070`, geography United States. Pulled {RENT_DATA_PULL_DATE}. |
| What is missing | **2020** has no standard 1-year ACS (the experimental 2020 1-year is not used). **2025** is not in that API on this pull. No month is invented. |
| Frequency and lag | Annual. The 1-year ACS for survey year Y is usually released the following September. This file dates the print at January of the survey year, the same revised-vintage convention as the rest of this note, not the release month and not ALFRED. Later months carry that print forward until the next survey year. 2020 carries 2019. August 2026 carries 2024. |
| Trial weight and range | {RENT_BURDEN_WEIGHT:.2f}, endpoints {rent_lo:g} to {rent_hi:g}. Higher share is less stable. In this file the annual 30%+ share runs **{_num(annual_burden[burden_low_year], 1)}** ({burden_low_year}) to **{_num(annual_burden[burden_high_year], 1)}** ({burden_high_year}). The range leaves that low short of fully stable and that high short of a hard floor. It was not chosen to push August under 70. A missing year drops the weight. None of these windows start before 2007. |

`v2_if_rent_burden` is h2 plus that 30% share. `v2_if_rent_burden_and_consumer` also adds `DRCCLACBS` at weight {CONSUMER_CREDIT_WEIGHT:.2f}. h2 stays the primary.

The last column is an honest high-frequency **proxy**, not rent burden. It is BLS `CUUR0000SEHA`, CPI-U rent of primary residence, not seasonally adjusted, 12-month percent change, same construction as headline CPI. Pulled {RENT_DATA_PULL_DATE}. Trial weight {RENT_CPI_PROXY_WEIGHT:.2f}, range {_signed(proxy_lo)} to {proxy_hi:g}. October 2025 is blank in this series (the appropriations lapse), so that month drops the proxy weight. The highest proxy print in these windows is **{_num(proxy_peak)}** on {proxy_peak_day}.

{chr(10).join(rent_lines)}

August 2026 is **{cell(aug_2026, 'v2_index')}** on h2. The rent-burden input that month is the **2024** ACS print carried forward: **{_num(aug_2026['v2_rent_burden_30'], 1)}%** of renters at the 30% line and **{_num(aug_2026['v2_rent_burden_50'], 1)}%** at the 50% line (observation {aug_2026['v2_rent_burden_observation_date']}). Adding the 30% share scores **{cell(aug_2026, 'v2_if_rent_burden_index')}**. Adding the 30% share and card delinquency scores **{cell(aug_2026, 'v2_if_rent_burden_and_consumer_index')}**. The rent-CPI proxy that month is **{_num(aug_2026['v2_rent_cpi_yoy'])}%** and scores **{cell(aug_2026, 'v2_if_rent_cpi_proxy_index')}**. The 2022, 2023, and 2024 surveys sit on top of each other near 52%, so carrying 2024 into August 2026 is not hiding a later collapse that this file contains. It also cannot see a 2025 or 2026 change in the income share, because those ACS years are not published here. Shelter inflation has cooled from the {proxy_peak_day[:7]} peak, which is why the proxy moves August less than the burden share does. Neither column puts August in Moderate.

October 2009’s burden print is the 2009 survey (**{_num(oct_2009['v2_rent_burden_30'], 1)}%** at 30%+, observation {oct_2009['v2_rent_burden_observation_date']}). h2 is **{cell(oct_2009, 'v2_index')}**. With the burden share it is **{cell(oct_2009, 'v2_if_rent_burden_index')}**. Rent of primary residence that month is only **{_num(oct_2009['v2_rent_cpi_yoy'])}%** year over year, so the proxy scores **{cell(oct_2009, 'v2_if_rent_cpi_proxy_index')}**. The income share and the rent-price change are different facts: burden rose through the recession while rent inflation slowed.

April 2020 has no 2020 ACS 1-year. The burden cell is the **2019** survey carried forward (**{_num(april['v2_rent_burden_30'], 1)}%**, the low in this file). h2 is **{cell(april, 'v2_index')}**. With that carried print it is **{cell(april, 'v2_if_rent_burden_index')}**. That is not a COVID rent-burden observation.

October 2008 uses the 2008 survey (**{_num(oct_2008['v2_rent_burden_30'], 1)}%**), which was not published until the following year. h2 is **{cell(oct_2008, 'v2_index')}** and h2 plus burden is **{cell(oct_2008, 'v2_if_rent_burden_index')}**. June 2022 uses the 2022 survey (**{_num(jun_2022['v2_rent_burden_30'], 1)}%**). h2 is **{cell(jun_2022, 'v2_index')}** and h2 plus burden is **{cell(jun_2022, 'v2_if_rent_burden_index')}**.

### Financing stress: Treasury yields

These columns are the cost of long-term borrowing. They are not mortgage delinquency, not rent burden, and not a corporate bond spread. BBB and high-yield OAS stay out of the replay.

The scored nominal series is the monthly mean of the daily 10-year Treasury constant-maturity yield, FRED `DGS10`. The companion is the monthly mean of the 10-year real yield, FRED `DFII10` (TIPS). Both files are the FRED graph CSV pulled {RATES_DATA_PULL_DATE}, daily prints through 24 September 2026, collapsed to a month mean. The fixture keeps January 2003 through August 2026. September 2026 is a partial month on this pull and is not stored. A missing month would drop the weight. Every month in these windows has a print, so the status is `observed`.

The scored input is the **level**, not the year-over-year change. August 2026 is {_num(aug_2026['v2_treasury_10y'])}% on the 10-year. That is the mortgage benchmark. A small change from a high level would still be expensive financing, and a drop during a crisis (October 2008, April 2020) is flight to Treasuries, not a sign that household borrowing was easy in every other sense. Higher yield is less stable.

| Piece | Choice |
| --- | --- |
| Nominal | `DGS10` monthly mean. Trial weight {TREASURY_10Y_WEIGHT:.2f}. Range {y10_lo:g} to {y10_hi:g}. In this file the monthly mean runs **{_num(treasury_sample[treasury_low])}** ({treasury_low}) to **{_num(treasury_sample[treasury_high])}** ({treasury_high}). |
| Real | `DFII10` monthly mean. Trial weight {REAL_YIELD_WEIGHT:.2f}. Range {_signed(real_lo_end)} to {real_hi_end:g}. In this file **{_num(real_sample[real_low])}** ({real_low}) to **{_num(real_sample[real_high])}** ({real_high}). |
| Why this range | Daily `DGS10` goes back to 1962 and the monthly mean peaked near 15 in the early 1980s. A 0-to-16 range would score a 4–5% yield as mostly calm. This side column is financing conditions in the same era as the real-yield series, which starts in 2003. The endpoints sit just outside that sample. They were not chosen to push August under 70. |
| Not scored | `T10Y2Y` (10-year minus 2-year) and `T10YIE` (breakeven inflation) were on the same FRED pull. The term spread steepened in the 2008 crisis while the real yield spiked, and a positive spread is not cheap long-term borrowing. Breakevens are already inside `DFII10`. Neither is a column. |

`v2_if_dgs10` is h2 plus the nominal yield. `v2_if_real_yield` is h2 plus the real yield. `v2_if_rates` is h2 plus both. h2 stays the primary.

{chr(10).join(rate_lines)}

August 2026 is **{cell(aug_2026, 'v2_index')}** on h2, **{cell(aug_2026, 'v2_if_dgs10_index')}** with the 10-year at {_num(aug_2026['v2_treasury_10y'])}%, **{cell(aug_2026, 'v2_if_real_yield_index')}** with the real yield at {_num(aug_2026['v2_real_yield_10y'])}%, and **{cell(aug_2026, 'v2_if_rates_index')}** with both. {rates_read}

October 2008 is the month the two yields disagree in a useful way. h2 is already **{cell(oct_2008, 'v2_index')}** on VIX. The nominal mean is {_num(oct_2008['v2_treasury_10y'])}% and h2 plus that yield is **{cell(oct_2008, 'v2_if_dgs10_index')}**, a nudge. The real yield is {_num(oct_2008['v2_real_yield_10y'])}% because breakevens had collapsed, close to the file high of {_num(real_sample[real_high])} in {real_high}. h2 plus the real yield is **{cell(oct_2008, 'v2_if_real_yield_index')}**. Both together are **{cell(oct_2008, 'v2_if_rates_index')}**. The nominal 10-year is not the stress in that month. The real yield is.

April 2020 is the other case. The 10-year mean is {_num(april['v2_treasury_10y'])}% and the real yield is {_num(april['v2_real_yield_10y'])}%. h2 is **{cell(april, 'v2_index')}**. With the 10-year it is **{cell(april, 'v2_if_dgs10_index')}**. Long rates were easy while employment had broken, so these columns do not mark the COVID labor trough.

October 2009 nominal is {_num(oct_2009['v2_treasury_10y'])}% (h2 **{cell(oct_2009, 'v2_index')}**, plus the 10-year **{cell(oct_2009, 'v2_if_dgs10_index')}**). June 2022 nominal is {_num(jun_2022['v2_treasury_10y'])}% (h2 **{cell(jun_2022, 'v2_index')}**, plus the 10-year **{cell(jun_2022, 'v2_if_dgs10_index')}**, plus both yields **{cell(jun_2022, 'v2_if_rates_index')}**).

### If debt, HUD, and Edelman stayed

h2 drops debt, homelessness, and Edelman trust. v1 held keeps them, and on the live formula August is the locked **{_num(aug_2026['v1_held_index'])}**. Those are different baskets. This section is the literal replacement on **h2**, before treating the drop as settled.

`v2_if_debt_included` adds debt-to-GDP at weight {DEBT_SENSITIVITY_WEIGHT:.2f} and the v1 endpoints (0 to 200) when that month has a print. `v2_if_kept_debt_hud_trust` adds that same debt rule plus homelessness **{HELD_CONSTANT_BASELINE['homelessness_rate']}** at the v1 weight {HUD_KEPT_WEIGHT:.2f} (range 0 to 0.5) and trust **{HELD_CONSTANT_BASELINE['trust_in_government']:.0f}** at the v1 weight {TRUST_KEPT_WEIGHT:.2f} (range 0 to 80, higher trust more stable). The HUD and Edelman numbers are the 19 September 2026 pins on every month. They are not a historical series. Crime stays on the h2 rule: absent months stay absent. The crime lock is not put back.

{chr(10).join(kept_lines)}

August 2026 on h2 is **{cell(aug_2026, 'v2_index')}**. Debt that month is the carried 2026 print (status {aug_2026['v1_debt_status']}). h2 plus debt is **{cell(aug_2026, 'v2_if_debt_included_index')}**. h2 plus debt and the two pins is **{cell(aug_2026, 'v2_if_kept_debt_hud_trust_index')}**. The live held basket is **{cell(aug_2026, 'v1_held_index')}**. On that live basket, dropping debt scores **{cell(aug_2026, 'v1_held_without_debt_index')}**, dropping homelessness scores **{cell(aug_2026, 'v1_held_without_homelessness_index')}**, and dropping trust scores **{cell(aug_2026, 'v1_held_without_trust_index')}**. Putting the three demoted inputs back on h2 does not reproduce 57.11. The live score still uses unemployment, the crime lock, and the v1 weights. h2 that month has a calm labor blend, calm VIX, and no crime trial.

June 2022 has no debt print in this replay ({jun_2022['v1_debt_status']}), so the kept column that month is h2 plus the two pins only: **{cell(jun_2022, 'v2_if_kept_debt_hud_trust_index')}** against h2 **{cell(jun_2022, 'v2_index')}**. October 2008 and April 2020 do have debt. Their kept scores are **{cell(oct_2008, 'v2_if_kept_debt_hud_trust_index')}** and **{cell(april, 'v2_if_kept_debt_hud_trust_index')}**.

### Inputs behind those months

{chr(10).join(raw_lines)}

### What the windows show

**Great Recession window.** The locked partial replay (inflation, unemployment, debt only) runs {_range_phrase(gfc_v1)}. All {gfc_v1['months_scored']} months are Moderate. Held-constant crime, homelessness, and trust keep that window Moderate as well ({_range_phrase(gfc_v1_held)}). The v2 candidate runs {_range_phrase(gfc_v2)}. The low is **October 2008 at {_num(gfc_v2['min_index'])} {_short_band(by_date[str(gfc_v2['min_date'])]['v2_band'])}**, with a VIX monthly mean of {_num(by_date['2008-10-01']['v2_vix_month_mean'])}. November is the VIX-mean peak at {_num(nov_2008['v2_vix_month_mean'])} (highest daily close {_num(nov_2008['v2_vix_month_max'])}) and scores **{_num(nov_2008['v2_index'])} {_short_band(nov_2008['v2_band'])}**, a bit higher than October because headline CPI had already cooled. The Low months are {', '.join(gfc_low_months)}. October 2009, the UNRATE peak at 10.0 and a labor blend of {_num(oct_2009['v2_labor_utilization'])}, is v1 partial **{_num(oct_2009['v1_partial_index'])} {_short_band(oct_2009['v1_partial_band'])}** and h2 **{_num(oct_2009['v2_index'])} {_short_band(oct_2009['v2_band'])}**. h1 scored October 2008 at 45.62 Low and October 2009 at 68.72 Moderate. {gap_read} There is no RTCI month in this window, so the v2 candidate and the crime-off series are the same path. {gfc_critical} None of the locked partial months leave Moderate.

**COVID window.** Locked partial runs {_range_phrase(covid_v1)}. April 2020 is **{_num(april['v1_partial_index'])} {_short_band(april['v1_partial_band'])}** partial and **{_num(april['v1_held_index'])} {_short_band(april['v1_held_band'])}** held constant (UNRATE 14.8, debt-to-GDP 132.66). Taking debt out of that held basket moves April to **{april_without_debt} {april_without_debt_band}**. Taking homelessness or trust out does not clear the Low band. Through the Great Recession window the held basket stays Moderate with or without debt, homelessness, or trust. The v2 candidate runs {_range_phrase(covid_v2)}. March 2020, the VIX monthly-mean peak at {_num(march['v2_vix_month_mean'])} (highest daily close {_num(march['v2_vix_month_max'])}), scores **{_num(march['v2_index'])} {_short_band(march['v2_band'])}** because the labor blend is still {_num(march['v2_labor_utilization'])}. April, when prime-age EPOP is {_num(april['v2_prime_age_epop'], 1)} and the blend is {_num(april['v2_labor_utilization'])}, scores **{_num(april['v2_index'])} {_short_band(april['v2_band'])}** (h1 was 48.32 Low). With crime excluded that month is **{_num(april['v2_without_crime_index'])} {_short_band(april['v2_without_crime_band'])}**, because the labor trough is a larger share of the {non_crime_weight:.2f} denominator. That is the same month without the trial crime input, not a second shock. Replacing the blend with UNRATE that month scores **{_num(april['v2_if_unrate_index'])} {_short_band(april['v2_if_unrate_band'])}**. The trial crime rate that month is {_num(april['v2_incident_rate'])}, not {PUBLISHED_INCIDENT_RATE:.0f}. Held-constant v1 for the whole year runs {_range_phrase(covid_v1_held)}.

**Recent path.** January 2022 through August 2026. Debt is excluded on the v1 partial column before October 2025: this pull does not contain 2022–2025Q3 `GFDEGDQ188S` prints, and those months are not filled by carrying 2020 forward. The 2022 v1 partial lows are inflation plus unemployment only. June 2022 is **{_num(jun_2022['v1_partial_index'])} {_short_band(jun_2022['v1_partial_band'])}** on that two-input v1 basket, and **{_num(jun_2022['v1_held_index'])} {_short_band(jun_2022['v1_held_band'])}** once crime, homelessness, and trust are pinned at the 2026 baselines.

October 2025 is a BLS gap. CPI, food, unemployment, EPOP, and participation were non-numeric (`-(X)` or `-(9)`) and are blank. v1 partial that month is debt alone (**{_num(oct_2025['v1_partial_index'])} {_short_band(oct_2025['v1_partial_band'])}**). The v2 candidate uses only `{oct_2025['v2_inputs_present']}` (denominator {_num(oct_2025['v2_weight_denominator'])}) and prints **{_num(oct_2025['v2_index'])} {_short_band(oct_2025['v2_band'])}**. That pair is the same thin month, not a crash and not a boom. Among recent months with all five trial inputs present, the v2 candidate runs {_num(full_recent['min'])} ({full_recent['min_date']}) to {_num(full_recent['max'])} ({full_recent['max_date']}).

From October 2025 the debt print on v1 is the published 122.56815. From January 2026 it is the fixture print 122.59387, carried the way the live publisher carries a quarter. August 2026 held-constant v1 is **{_num(aug_2026['v1_held_index'])}**, the same six inputs as the locked 57.11. The v2 candidate that month is **{_num(aug_2026['v2_index'])} {_short_band(aug_2026['v2_band'])}** with crime excluded (the RTCI file ends April 2026, trial rate {_num(apr_2026['v2_incident_rate'])}). The gap versus 57.11 is the basket: debt, homelessness, and trust are out, and the labor blend and VIX are calm. It is not a claim that stability improved inside v1.0.0.

Food CPI year-over-year uses the h2 range {food_lo_txt} to {food_hi_txt}. {food_above_sentence} {food_below_sentence} {len(food_mild_negative)} months have negative food inflation inside that range, so they lean stable without scoring fully stable. {len(food_above_h1_floor)} months are above the h1 ceiling of 10 ({', '.join(food_above_h1_floor)}). Under h1 those months clamped food at fully unstable. June 2022 food is {_num(jun_2022['v2_food_cpi_yoy'], 1)} and September 2022 is {_num(sep_2022['v2_food_cpi_yoy'], 1)}; the h2 candidate those months is {_num(jun_2022['v2_index'])} and {_num(sep_2022['v2_index'])}. {food_move} The recent-window low on the v2 candidate, including thin months, is **{_num(recent_v2['min_index'])} on {recent_v2['min_date']}**.

## Crime trial, and why 2008 cannot use it

The RTCI cleaned file in this pull covers **January 2018 through April 2026**. The 2008 window has no trial rate. Fair replay does not backfill those months with the locked 2723, with a later RTCI month, or with a different crime series.

The live fetcher still returns `incident_rate` **{PUBLISHED_INCIDENT_RATE:.0f}** and does not score the file. Its diagnostic month is the latest calendar month in the RTCI file, parsed from the date rather than a text sort of the month name. This replay uses that same calendar month, and it does not change the lock. September 2025 in the file is a trial rate of about {_num(by_date['2025-09-01']['v2_incident_rate'])}, not 2723. Every usable month in this download has **621** agencies. That is a balanced sample, not a national census, and the rate's level is not comparable to a historical UCR series that this repo does not reconstruct.

From May 2026 through August 2026 the primary candidate excludes crime again, so the denominator changes. Compare those months with `v2_without_crime_index` before reading a jump as stress or relief.

## Debt, homelessness, trust, and UNRATE

Homelessness and trust cannot be replayed. The held-constant columns pin them at **0.23** and **41**. Removing one of them is `v1_held_without_homelessness` or `v1_held_without_trust` in the monthly CSV. That is the locked formula with one held input left out. It is not a historical path for that series.

Debt is historical inside the 2008 and 2020 windows (the locked fixture, including ordinary within-quarter carry-forward). It is not historical for most of the recent window. Adding it back onto the v2 basket only changes the score in months where a print is actually in hand.

UNRATE remains the v1 labor input. The composite is lower in April 2020 than a calm month, and it does not by itself mark October 2009 as the Great Recession trough. `v2_if_unrate` and `v2_if_epop_only` are in the CSV for that comparison. The blend and the EPOP-only range are hypotheses that bracket this sample. They are not estimated endpoints.

## What still blocks a v2.0 contract

- These weights and ranges are hypothesis h2. They were not fit to a loss, a utility function, or a decision threshold. h1 is the prior labeled basket, not a rejected contract.
- Rent burden is a side column, not part of h2. It is ACS 1-year `B25070` (30%+ of income), annual, carried forward from the survey-year January. The latest survey in this pull is 2024. There is no 2020 standard 1-year and no 2025 1-year here, and neither gap is filled. The 50%+ share is diagnostic only. `CUUR0000SEHA` year-over-year is a labeled rent-inflation proxy, not the income share. Neither series is in the live score.
- A household survey of missed housing payments is still not in the replay. Bank delinquency still ends at 2026 Q2.
- Treasury yields are side columns, not part of h2. `DGS10` is the nominal 10-year level and `DFII10` is the real 10-year level. `T10Y2Y` and `T10YIE` are not scored. Corporate credit spreads are still not in the replay. VIX is an equity-volatility index, not a credit spread. Card delinquency (`DRCCLACBS`, issue #48) is a side column only. It is not a BBB or high-yield OAS series.
- The labor composite is not the incubating participation penalty. That penalty still has no formula. The h2 band 72–82 is a tighter hypothesis range, not that penalty.
- The h2 food range {food_lo_txt} to {food_hi_txt} is still a draft. Prints outside it still clamp. h1's 0–10 range is what clamped the 2022 peak at fully unstable and mild deflation at fully stable.
- Crime has no fair 2008 path from RTCI. The published input remains locked at 2723. Agency coverage and the 12-month RTCI definition are not a national historical crime rate.
- Homelessness and Edelman trust still have no monthly history. `v2_if_kept_debt_hud_trust` pins them at the 19 September 2026 values so the demotion can be compared with leaving them in. That pin is not a 2008 or 2020 observation.
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
        "v2_if_rent_burden_index": "#7c3aed",
        "v2_if_dgs10_index": "#9f1239",
    }
    dashes = {
        "v2_without_crime_index": "4 3",
        "v2_if_rent_burden_index": "1 3",
        "v2_if_dgs10_index": "6 3",
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
                        lines.append((color, points, dashes.get(key)))
                        points = []
                    continue
                points.append(xy(i, float(row[key])))
            if points:
                lines.append((color, points, dashes.get(key)))
        path_markup = []
        for color, points, dashed in lines:
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            dash = f' stroke-dasharray="{dashed}"' if dashed else ""
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
        '<tspan fill="#b45309">   v2 candidate h2</tspan>'
        '<tspan fill="#0f766e">   v2 crime off</tspan>'
        '<tspan fill="#7c3aed">   h2 + rent burden</tspan>'
        '<tspan fill="#9f1239">   h2 + 10y</tspan>'
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
