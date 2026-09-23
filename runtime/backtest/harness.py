# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Mechanical v1.0.0 replay of historical FRED levels.

This is the start of issue #55, not the historical essay. It does not change
the weekly publisher, the formula, the bands, or the published site.

The score for every row comes from ``runtime.processing.formula.compute_index``
(endpoints, weights, trust inversion, clamp, and divide-by-sum-of-weights).
Only three inputs are historical:

* inflation — CPIAUCSL year-over-year percent, built the same way as
  ``fetch_inflation_rate.fetch`` (same calendar month one year earlier)
* unemployment — UNRATE level, as ``fetch_unemployment_rate`` stores it
* debt-to-GDP — GFDEGDQ188S level, as ``fetch_debt_to_gdp_ratio`` stores it

Crime, homelessness, and trust are not reconstructed. ``partial`` leaves them
out and lets the formula shrink the weight denominator. ``held_constant``
pins them to the published 19 September 2026 baselines and labels every one
of those cells ``held_constant``. Neither mode is a six-metric history.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

from runtime.data.fetch.fetch_debt_to_gdp_ratio import SERIES_ID as DEBT_SERIES_ID
from runtime.data.fetch.fetch_inflation_rate import SERIES_ID as CPI_SERIES_ID
from runtime.data.fetch.fetch_unemployment_rate import SERIES_ID as UNEMPLOYMENT_SERIES_ID
from runtime.processing.formula import CORE_METRICS, WEIGHTS, compute_index, interpret
from runtime.util.http_retry import RetryError, get_with_retry
from runtime.util.secrets_compat import get_secret

METHODOLOGY_VERSION = "1.0.0"
PUBLISHED_DATE = "2026-09-19"
# Public FRED graph vintage recorded in runtime/backtest/fixtures/.
# A later live pull stamps its own download date. Neither is an ALFRED real-time vintage.
FIXTURE_DOWNLOAD_DATE = "2026-09-23"

# Named baseline for held_constant mode. These are the published inputs on
# PUBLISHED_DATE, not historical observations of crime, homelessness, or trust.
HELD_CONSTANT_BASELINE = {
    "name": "published_2026-09-19",
    "incident_rate": 2723.0,
    "homelessness_rate": 0.23,
    "trust_in_government": 41.0,
}

SPARSE_METRICS = (
    "incident_rate",
    "homelessness_rate",
    "trust_in_government",
)
FRED_METRICS = (
    "inflation_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
)

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_ID = {
    "cpi": CPI_SERIES_ID,
    "unemployment": UNEMPLOYMENT_SERIES_ID,
    "debt_to_gdp": DEBT_SERIES_ID,
}

SCORE_NOTES = {
    "partial": (
        "Partial v1.0.0 replay. Missing inputs are excluded and the weight "
        "denominator shrinks to the sum of present weights. Crime, homelessness, "
        "and trust are excluded, not historical observations."
    ),
    "held_constant": (
        "v1.0.0 replay. Crime, homelessness, and trust are held_constant at "
        "published_2026-09-19 (2723 / 0.23 / 41). Those three are not historical "
        "observations."
    ),
}

COLUMNS = (
    "date",
    "window",
    "window_start",
    "window_end",
    "methodology_version",
    "fred_download_date",
    "score_mode",
    "replay_index",
    "band",
    "weight_denominator",
    "inputs_present",
    "inputs_excluded",
    "inputs_held_constant",
    "held_constant_baseline",
    "inflation_rate",
    "inflation_rate_status",
    "inflation_cpi",
    "inflation_cpi_date",
    "inflation_cpi_prior",
    "inflation_cpi_prior_date",
    "unemployment_rate",
    "unemployment_rate_status",
    "debt_to_gdp_ratio",
    "debt_to_gdp_ratio_status",
    "debt_to_gdp_ratio_observation_date",
    "incident_rate",
    "incident_rate_status",
    "homelessness_rate",
    "homelessness_rate_status",
    "trust_in_government",
    "trust_in_government_status",
    "score_note",
)

OUTPUT_FILES = {
    "partial": "replay_partial.csv",
    "held_constant": "replay_held_constant.csv",
}

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-01$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = PACKAGE_DIR / "fixtures"
OUTPUT_DIR = PACKAGE_DIR / "output"
ROOT = Path(__file__).resolve().parents[2]
WEEKLY_CSV = ROOT / "runtime" / "data" / "weekly_bugout_index.csv"


class MissingFredKey(RuntimeError):
    """``--source fred`` was asked to run without ``FRED_API_KEY``."""


class FredFetchError(RuntimeError):
    """FRED did not return a usable series. No replay rows were invented."""


@dataclass(frozen=True)
class Window:
    """Inclusive month range. Dates are FRED-style ``YYYY-MM-01``."""

    name: str
    start: str
    end: str
    description: str


# NBER dates are the window rationale. The table itself is monthly FRED dates.
WINDOWS = {
    "2008": Window(
        name="2008",
        start="2007-12-01",
        end="2009-12-01",
        description=(
            "NBER Great Recession, December 2007–June 2009, extended through "
            "December 2009 so the October 2009 unemployment peak is in the table."
        ),
    ),
    "2020": Window(
        name="2020",
        start="2020-01-01",
        end="2020-12-01",
        description=(
            "Calendar 2020. The NBER COVID-19 recession is February–April 2020. "
            "January is included so the pre-shock unemployment rate is visible; "
            "the rest of the year shows the partial rebound."
        ),
    ),
}
WINDOW_ORDER = ("2008", "2020")


@dataclass(frozen=True)
class FredLevels:
    """CPI levels, unemployment levels, and quarterly debt-to-GDP levels."""

    cpi: Mapping[str, float]
    unemployment: Mapping[str, float]
    debt_to_gdp: Mapping[str, float]


def prior_year_date(current_date: str) -> str:
    """Same calendar date one year earlier.

    Matches ``fetch_inflation_rate``: ``str(int(current_date[:4]) - 1) + current_date[4:]``.
    """
    return str(int(current_date[:4]) - 1) + current_date[4:]


def cpi_yoy(current_cpi: float, previous_cpi: float) -> float:
    """Year-over-year percent change.

    Matches ``fetch_inflation_rate``:
    ``((current_cpi - previous_cpi) / previous_cpi) * 100``.
    """
    return ((current_cpi - previous_cpi) / previous_cpi) * 100


def iter_months(start: str, end: str) -> list[str]:
    """First-of-month dates from ``start`` through ``end``, inclusive."""
    if not _MONTH.match(start) or not _MONTH.match(end):
        raise ValueError(f"windows must be YYYY-MM-01 dates, got {start!r}..{end!r}")
    if start > end:
        raise ValueError(f"{start} is after {end}")
    year, month, _day = (int(part) for part in start.split("-"))
    months = []
    while True:
        day = f"{year:04d}-{month:02d}-01"
        months.append(day)
        if day == end:
            return months
        month += 1
        if month == 13:
            month = 1
            year += 1


def _valid_day(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not _DAY.match(text[:10] if len(text) >= 10 else text):
        return None
    return text[:10]


def parse_observations(raw_observations: list) -> dict[str, float]:
    """Map FRED ``date`` to float. Placeholder ``.`` rows are dropped."""
    points: dict[str, float] = {}
    for obs in raw_observations or []:
        if not isinstance(obs, dict):
            continue
        day = _valid_day(obs.get("date", obs.get("observation_date")))
        if day is None:
            continue
        raw_value = obs.get("value")
        if raw_value in (".", "", None):
            continue
        try:
            points[day] = float(raw_value)
        except (TypeError, ValueError):
            continue
    return points


def parse_series_csv(text: str) -> dict[str, float]:
    """Read a FRED graph CSV (``observation_date`` plus one value column)."""
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError("series CSV needs a date column and a value column")
    date_key = reader.fieldnames[0]
    value_key = reader.fieldnames[1]
    points: dict[str, float] = {}
    for row in reader:
        day = _valid_day(row.get(date_key))
        raw_value = (row.get(value_key) or "").strip()
        if day is None or raw_value in ("", "."):
            continue
        points[day] = float(raw_value)
    return points


def load_fixtures(directory: Optional[Path] = None) -> FredLevels:
    """Recorded FRED sample. Pytest uses this so a live key is not required."""
    folder = FIXTURE_DIR if directory is None else directory
    return FredLevels(
        cpi=parse_series_csv((folder / "CPIAUCSL.csv").read_text(encoding="utf-8")),
        unemployment=parse_series_csv((folder / "UNRATE.csv").read_text(encoding="utf-8")),
        debt_to_gdp=parse_series_csv((folder / "GFDEGDQ188S.csv").read_text(encoding="utf-8")),
    )


def fred_request_range(windows: Sequence[str]) -> tuple[str, str]:
    """Observation start/end for a FRED pull.

    CPI year-over-year needs the same month one year before the first window
    month. Debt's previous quarter falls inside that year as well.
    """
    if not windows:
        raise ValueError("at least one window is required")
    starts = []
    ends = []
    for name in windows:
        window = WINDOWS[name]
        starts.append(window.start)
        ends.append(window.end)
    return prior_year_date(min(starts)), max(ends)


def fetch_fred_series(
    series_id: str,
    observation_start: str,
    observation_end: str,
    api_key: str,
    request=None,
) -> dict[str, float]:
    """One FRED series over a date range. Same API and key as the live fetchers."""
    getter = get_with_retry if request is None else request
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": observation_start,
        "observation_end": observation_end,
        "sort_order": "asc",
    }
    try:
        response = getter(FRED_API_BASE_URL, params=params)
    except RetryError as exc:
        raise FredFetchError(f"{series_id}: FRED unreachable: {exc}") from exc
    try:
        payload = response.json()
    except (AttributeError, ValueError) as exc:
        raise FredFetchError(f"{series_id}: FRED response parse error: {exc}") from exc
    observations = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(observations, list):
        raise FredFetchError(f"{series_id}: FRED response missing observations")
    points = parse_observations(observations)
    if not points:
        raise FredFetchError(f"{series_id}: no observations")
    return points


def fetch_fred_levels(
    windows: Sequence[str] = WINDOW_ORDER,
    api_key: Optional[str] = None,
    request=None,
) -> FredLevels:
    """Pull CPI, unemployment, and debt-to-GDP. Requires ``FRED_API_KEY``."""
    if api_key is None:
        api_key = get_secret("FRED_API_KEY")
    if not api_key:
        raise MissingFredKey("FRED_API_KEY not set")
    start, end = fred_request_range(windows)
    return FredLevels(
        cpi=fetch_fred_series(FRED_SERIES_ID["cpi"], start, end, api_key, request=request),
        unemployment=fetch_fred_series(
            FRED_SERIES_ID["unemployment"], start, end, api_key, request=request
        ),
        debt_to_gdp=fetch_fred_series(
            FRED_SERIES_ID["debt_to_gdp"], start, end, api_key, request=request
        ),
    )


def _inflation_fields(cpi: Mapping[str, float], day: str) -> dict:
    prior_day = prior_year_date(day)
    current = cpi.get(day)
    previous = cpi.get(prior_day)
    if current is None or previous is None or previous == 0:
        rate = None
        status = "excluded"
    else:
        rate = cpi_yoy(current, previous)
        status = "observed"
    return {
        "inflation_rate": rate,
        "inflation_rate_status": status,
        "inflation_cpi": current,
        "inflation_cpi_date": day if current is not None else "",
        "inflation_cpi_prior": previous,
        "inflation_cpi_prior_date": prior_day if previous is not None else "",
    }


def _unemployment_fields(series: Mapping[str, float], day: str) -> dict:
    if day not in series:
        return {"unemployment_rate": None, "unemployment_rate_status": "excluded"}
    return {"unemployment_rate": series[day], "unemployment_rate_status": "observed"}


def _debt_fields(series: Mapping[str, float], day: str) -> dict:
    """Latest quarterly print on or before ``day``.

    Quarter-start months are ``observed``. Later months in the quarter are
    ``carried_forward`` and keep the quarter's observation date. This is the
    published quarterly level, not an interpolation and not a guess.
    """
    available = [stamp for stamp in series if stamp <= day]
    if not available:
        return {
            "debt_to_gdp_ratio": None,
            "debt_to_gdp_ratio_status": "excluded",
            "debt_to_gdp_ratio_observation_date": "",
        }
    chosen = max(available)
    status = "observed" if chosen == day else "carried_forward"
    return {
        "debt_to_gdp_ratio": series[chosen],
        "debt_to_gdp_ratio_status": status,
        "debt_to_gdp_ratio_observation_date": chosen,
    }


def _sparse_fields(mode: str) -> dict:
    """Crime, homelessness, and trust. Never read from a historical series."""
    fields = {}
    if mode == "partial":
        for metric in SPARSE_METRICS:
            fields[metric] = None
            fields[f"{metric}_status"] = "excluded"
        return fields
    if mode == "held_constant":
        for metric in SPARSE_METRICS:
            fields[metric] = float(HELD_CONSTANT_BASELINE[metric])
            fields[f"{metric}_status"] = "held_constant"
        return fields
    raise ValueError(f"unknown score mode {mode!r}")


def _join(names: Sequence[str]) -> str:
    return "|".join(names)


def build_month_row(
    levels: FredLevels,
    day: str,
    window: Window,
    mode: str,
    fred_download_date: str = FIXTURE_DOWNLOAD_DATE,
) -> dict:
    """One replay row. The index is ``compute_index``; sparse inputs are not historical."""
    if mode not in SCORE_NOTES:
        raise ValueError(f"unknown score mode {mode!r}")
    if not _MONTH.match(day):
        raise ValueError(f"replay dates must be YYYY-MM-01, got {day!r}")

    fields = {}
    fields.update(_inflation_fields(levels.cpi, day))
    fields.update(_unemployment_fields(levels.unemployment, day))
    fields.update(_debt_fields(levels.debt_to_gdp, day))
    fields.update(_sparse_fields(mode))

    values = {metric: fields[metric] for metric in CORE_METRICS}
    payload = {
        metric: {"data": {metric: value}}
        for metric, value in values.items()
        if value is not None
    }
    scored = compute_index(payload)
    present = [metric for metric in CORE_METRICS if scored["metrics"][metric]["raw"] is not None]
    excluded = [metric for metric in CORE_METRICS if metric not in present]
    held = [metric for metric in SPARSE_METRICS if fields[f"{metric}_status"] == "held_constant"]

    row = {
        "date": day,
        "window": window.name,
        "window_start": window.start,
        "window_end": window.end,
        "methodology_version": METHODOLOGY_VERSION,
        "fred_download_date": fred_download_date,
        "score_mode": mode,
        "replay_index": scored["index"],
        "band": interpret(scored["index"])["band"],
        "weight_denominator": sum(WEIGHTS[metric] for metric in present),
        "inputs_present": _join(present),
        "inputs_excluded": _join(excluded),
        "inputs_held_constant": _join(held),
        "held_constant_baseline": HELD_CONSTANT_BASELINE["name"] if held else "",
        "score_note": SCORE_NOTES[mode],
    }
    row.update(fields)
    return row


def replay_date(
    levels: FredLevels,
    day: str,
    mode: str,
    fred_download_date: str = FIXTURE_DOWNLOAD_DATE,
) -> dict:
    """Score one month. Used for the locked 19 September check, not the crisis CSV."""
    window = Window(name="single_month", start=day, end=day, description="single observation month")
    return build_month_row(levels, day, window, mode, fred_download_date=fred_download_date)


def build_replay(
    levels: FredLevels,
    windows: Sequence[str] = WINDOW_ORDER,
    mode: str = "partial",
    fred_download_date: str = FIXTURE_DOWNLOAD_DATE,
) -> list[dict]:
    """Rows for each month of each window, in window order."""
    rows = []
    for name in windows:
        try:
            window = WINDOWS[name]
        except KeyError:
            known = ", ".join(WINDOW_ORDER)
            raise KeyError(f"unknown window {name!r}; known windows: {known}") from None
        for day in iter_months(window.start, window.end):
            rows.append(
                build_month_row(
                    levels, day, window, mode, fred_download_date=fred_download_date
                )
            )
    return rows


def format_float(value: float) -> str:
    """Shortest round-trip, without a trailing ``.0`` on whole numbers."""
    text = repr(value)
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        return text[:-2]
    return text


def csv_fields(row: Mapping[str, object]) -> dict[str, str]:
    """String cells for the CSV. Missing numbers stay blank."""
    rendered = {}
    for column in COLUMNS:
        value = row[column]
        if value is None or value == "":
            rendered[column] = ""
        elif column in ("replay_index", "weight_denominator"):
            rendered[column] = f"{float(value):.2f}"
        elif isinstance(value, float):
            rendered[column] = format_float(value)
        else:
            rendered[column] = str(value)
    return rendered


def write_replay(rows: Sequence[Mapping[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(csv_fields(row))


def write_windows(
    levels: FredLevels,
    output_dir: Path,
    windows: Sequence[str] = WINDOW_ORDER,
    modes: Sequence[str] = ("partial", "held_constant"),
    fred_download_date: str = FIXTURE_DOWNLOAD_DATE,
) -> list[Path]:
    written = []
    for mode in modes:
        path = output_dir / OUTPUT_FILES[mode]
        write_replay(
            build_replay(levels, windows, mode, fred_download_date=fred_download_date),
            path,
        )
        written.append(path)
    return written


def load_published_raws(
    path: Path = WEEKLY_CSV,
    publication_date: str = PUBLISHED_DATE,
) -> dict[str, float]:
    """Six raw inputs from the weekly history. This does not fetch FRED."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["date"] == publication_date]
    if len(rows) != 1:
        raise ValueError(f"expected one {publication_date} row in {path}, found {len(rows)}")
    row = rows[0]
    return {metric: float(row[metric]) for metric in CORE_METRICS}


def score_published_inputs(raws: Mapping[str, float]) -> dict:
    """Score a complete six-metric snapshot with the live formula.

    This is the lock check for the 19 September 2026 inputs. It refuses a
    partial snapshot so a missing crime or trust figure cannot be dropped
    quietly and still called 57.11.
    """
    missing = [metric for metric in CORE_METRICS if metric not in raws or raws[metric] is None]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"locked check needs all six published inputs; missing {joined}")
    payload = {metric: {"data": {metric: float(raws[metric])}} for metric in CORE_METRICS}
    return compute_index(payload)
