# BugOutIndex
# Copyright (C) 2025 Your Name or Organization
#
# This file is dual-licensed under the AGPL-3.0 and a commercial license.
#
# You may use, modify, and distribute this software under the terms of the
# GNU Affero General Public License v3.0 as published by the Free Software Foundation.
#
# For proprietary or commercial use, please contact: your-email@example.com
import calendar
import os
from collections import Counter
from datetime import datetime
from typing import Optional, Sequence

"""
Fetcher for the violent-plus-property crime incident rate.

Methodology 1.1.0 scores the population-weighted national rate for the latest
calendar month in the AH-Datalytics RTCI cleaned file. That rate is RTCI's
Nationwide Full Sample row when the row is reliable. Otherwise it is the
population-weighted total of the other usable rows, which matches the
Nationwide row when the row is good. ``PUBLISHED_INCIDENT_RATE`` (2723.0) is
the methodology 1.0.0 lock. It is not the scored input.

The month is the latest calendar month in the file. RTCI writes ``Date`` as
a month name (``format(as.Date(date), "%B %Y")`` in ``final_sample_to_viz.R``)
and also writes numeric ``Month`` and ``Year``. Sorting the ``Date`` text
picks September over April and over December. The month is parsed instead.
The observation date is the last day of that month. It comes from the file.
A download failure or a month with no usable rate fails the fetch. The weekly
job then refuses to publish. It does not invent a rate or a date, and it does
not carry the previous crime value forward.
"""

# Resolve path relative to this file so it works from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))

# Methodology 1.0.0 crime lock (old unweighted print). The backtest holds
# this as the 19 September 2026 baseline. Methodology 1.1.0 does not score it.
PUBLISHED_INCIDENT_RATE = 2723.0

# RTCI aggregate identity for the national figure. One row per month on the
# cleaned file: Agency "Full Sample", State "Nationwide".
NATIONWIDE_FULL_SAMPLE_AGENCY = "Full Sample"
NATIONWIDE_FULL_SAMPLE_STATE = "Nationwide"
RATE_SOURCE_NATIONWIDE = "nationwide_full_sample"
RATE_SOURCE_WEIGHTED = "population_weighted"
# One cent is rounding. A wider gap means the row is not the weighted total.
NATIONWIDE_RATE_TOLERANCE = 0.02

# Full and abbreviated English month names, plus the numeric month RTCI
# stores in the Month column. Text order of these names is not calendar order.
_MONTH_INDEX = {}
for _number in range(1, 13):
    _MONTH_INDEX[calendar.month_name[_number].lower()] = _number
    _MONTH_INDEX[calendar.month_abbr[_number].lower()] = _number

_MISSING = {"", "nan", "none", "nat", "<na>", "na"}


def _clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in _MISSING:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def _month_number(value) -> Optional[int]:
    text = _clean_text(value)
    if not text:
        return None
    if text.isdigit():
        number = int(text)
        if 1 <= number <= 12:
            return number
        return None
    return _MONTH_INDEX.get(text.lower().rstrip("."))


def _year_number(value) -> Optional[int]:
    text = _clean_text(value)
    if len(text) == 4 and text.isdigit():
        year = int(text)
        if 1900 <= year <= 2200:
            return year
    return None


def _period_from_label(label) -> Optional[tuple]:
    """Calendar ``(year, month)`` from one RTCI date value.

    The cleaned file's ``Date`` column is ``"%B %Y"`` (``April 2026``).
    Older or alternate exports also show up as an abbreviated name, an ISO
    day, or a year-month. A ``datetime`` / pandas timestamp is read from its
    year and month attributes.
    """
    if label is not None and not isinstance(label, str):
        year = getattr(label, "year", None)
        month = getattr(label, "month", None)
        try:
            if year is not None and month is not None and not isinstance(year, str):
                year_n = int(year)
                month_n = int(month)
                if 1 <= month_n <= 12 and 1900 <= year_n <= 2200:
                    return (year_n, month_n)
        except (TypeError, ValueError):
            pass
    text = _clean_text(label)
    if not text:
        return None
    cleaned = " ".join(text.replace(",", " ").split())
    parts = cleaned.split()
    # A spelled month wins over a leading day number ("30 April 2026").
    named_months = [
        _MONTH_INDEX[part.lower().rstrip(".")]
        for part in parts
        if part.lower().rstrip(".") in _MONTH_INDEX
    ]
    named_years = [year for year in (_year_number(part) for part in parts) if year]
    if named_months and named_years:
        return (named_years[-1], named_months[0])
    head = text[:10] if len(text) >= 10 and text[4] in "-/" and text[7] in "-/" else text
    for candidate in (head, text):
        if len(candidate) >= 7 and candidate[4] in "-/" and candidate[:4].isdigit():
            bits = candidate.split(candidate[4])
            if len(bits) >= 2:
                year = _year_number(bits[0])
                month = _month_number(bits[1])
                if year and month:
                    return (year, month)
    if "/" in text:
        bits = text.split("/")
        if len(bits) == 2:
            month = _month_number(bits[0])
            year = _year_number(bits[1])
            if month and year:
                return (year, month)
        if len(bits) == 3:
            month = _month_number(bits[0])
            year = _year_number(bits[2])
            if month and year:
                return (year, month)
    return None


def parse_rtci_period(date_label=None, month=None, year=None) -> Optional[tuple]:
    """Calendar ``(year, month)`` for one RTCI row.

    Numeric ``Month`` and ``Year`` win when both are present. Those columns
    are the calendar fields. ``Date`` is a display string, and a text sort of
    that string is not a date. When the columns are absent, ``Date`` is parsed.
    """
    from_columns = None
    month_n = _month_number(month)
    year_n = _year_number(year)
    if month_n and year_n:
        from_columns = (year_n, month_n)
    if from_columns is not None:
        return from_columns
    return _period_from_label(date_label)


def period_label(year: int, month: int) -> str:
    """Canonical ``Month YYYY`` label, matching the RTCI ``Date`` text."""
    return f"{calendar.month_name[month]} {year}"


def period_end(year: int, month: int) -> str:
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last:02d}"


def _latest_period(periods: Sequence[Optional[tuple]]) -> Optional[tuple]:
    valid = [period for period in periods if period]
    if not valid:
        return None
    return max(valid)


def crime_file_provenance(date_labels, last_updated, months=None, years=None) -> dict:
    """Dating for the RTCI file. Does not choose the scored rate.

    ``value_month`` and ``file_through`` are both the latest calendar month.
    They used to differ: ``value_month`` was ``max()`` on the month-name
    strings, so September sorted after April and December.
    """
    labels = list(date_labels)
    month_values = list(months) if months is not None else [None] * len(labels)
    year_values = list(years) if years is not None else [None] * len(labels)
    if len(month_values) != len(labels) or len(year_values) != len(labels):
        raise ValueError("Month and Year must align with Date")
    periods = [
        parse_rtci_period(label, month, year)
        for label, month, year in zip(labels, month_values, year_values)
    ]
    latest = _latest_period(periods)
    if latest is None:
        return {"kind": "file"}
    value_month = period_label(*latest)
    updated = []
    for raw in last_updated:
        text = str(raw).strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            try:
                datetime.strptime(text[:10], "%Y-%m-%d")
            except ValueError:
                continue
            updated.append(text[:10])
    provenance = {
        "kind": "file",
        "value_month": value_month,
        "value_month_end": period_end(*latest),
        "file_through": value_month,
    }
    if updated:
        provenance["file_updated"] = Counter(updated).most_common(1)[0][0]
    return provenance


def _frame_periods(frame) -> list:
    dates = frame["Date"].tolist()
    months = frame["Month"].tolist() if "Month" in frame.columns else [None] * len(dates)
    years = frame["Year"].tolist() if "Year" in frame.columns else [None] * len(dates)
    return [
        parse_rtci_period(label, month, year)
        for label, month, year in zip(dates, months, years)
    ]


def _provenance_from_frame(frame) -> dict:
    updated = frame["Last Updated"].tolist() if "Last Updated" in frame.columns else []
    months = frame["Month"].tolist() if "Month" in frame.columns else None
    years = frame["Year"].tolist() if "Year" in frame.columns else None
    return crime_file_provenance(frame["Date"].tolist(), updated, months, years)


def _rates_for_month(frame, month: str) -> dict:
    """Unweighted mean of usable rows, and the population-weighted total.

    Each usable row contributes one rate:
    ``(Violent Crime_mvs_12mo + Property Crime_mvs_12mo) / FBI.Population.Covered × 100,000``.
    The unweighted figure is the mean of those rates, rounded to two decimals.
    Each row counts once. It is not a population-weighted national total.

    A row is usable when both 12-month counts are present and population is
    positive. The cleaned file also contains RTCI aggregate rows (state and
    nationwide "Full Sample", and population-band aggregates). Those rows stay
    in this mean. That inclusion is the construction behind the methodology
    1.0.0 lock of 2723.0 (399 usable rows on the old local file, September
    2024). The unweighted mean is diagnostic under 1.1.0. It is not the scored
    input.

    The population-weighted figure is the sum of crimes divided by the sum of
    population on the same rows. On the cleaned file that figure matches the
    Nationwide Full Sample row, because the aggregate rows are partitions of
    the same counts and do not change the ratio.

    ``month`` is matched by parsed calendar month, so ``April 2026``,
    ``Apr 2026``, and ``2026-04-01`` describe the same month.
    """
    import pandas as pd

    target = _period_from_label(month)
    if target is None:
        raise ValueError(f"no parseable month for {month}")
    periods = _frame_periods(frame)
    mask = pd.Series([period == target for period in periods], index=frame.index)
    slice_ = frame.loc[mask]
    violent = pd.to_numeric(slice_["Violent Crime_mvs_12mo"], errors="coerce")
    prop = pd.to_numeric(slice_["Property Crime_mvs_12mo"], errors="coerce")
    pop = pd.to_numeric(slice_["FBI.Population.Covered"], errors="coerce")
    total = violent + prop
    usable = total.notna() & pop.notna() & (pop > 0)
    if not bool(usable.any()):
        raise ValueError(f"no usable agency rows for {period_label(*target)}")
    rates = (total[usable] / pop[usable]) * 100000
    unweighted = float(round(float(rates.mean()), 2))
    weighted = float(round(float(total[usable].sum() / pop[usable].sum() * 100000), 2))
    return {
        "unweighted": unweighted,
        "population_weighted": weighted,
        "agencies": int(usable.sum()),
    }


def _nationwide_full_sample_mask(frame):
    """Rows RTCI labels as the Nationwide Full Sample, or None if those columns are absent."""
    if "Agency" not in frame.columns or "State" not in frame.columns:
        return None
    agency = frame["Agency"].map(lambda value: _clean_text(value).casefold())
    state = frame["State"].map(lambda value: _clean_text(value).casefold())
    return (agency == NATIONWIDE_FULL_SAMPLE_AGENCY.casefold()) & (
        state == NATIONWIDE_FULL_SAMPLE_STATE.casefold()
    )


def _without_nationwide_full_sample(frame):
    mask = _nationwide_full_sample_mask(frame)
    if mask is None:
        return frame
    return frame.loc[~mask]


def _finite_number(value):
    import pandas as pd

    number = pd.to_numeric(value, errors="coerce")
    try:
        number = float(number)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _month_slice(frame, month: str):
    import pandas as pd

    target = _period_from_label(month)
    if target is None:
        raise ValueError(f"no parseable month for {month}")
    periods = _frame_periods(frame)
    mask = pd.Series([period == target for period in periods], index=frame.index)
    return frame.loc[mask]


def _nationwide_rate_for_month(frame, month: str):
    """``(rate or None, row_count)`` for Nationwide Full Sample rows in ``month``.

    ``row_count`` includes unusable rows. ``rate`` is set only when exactly
    one row matches and both 12-month counts and a positive population are
    present. The rate is rounded to two decimals, same as the weighted total.
    """
    if _nationwide_full_sample_mask(frame) is None:
        return None, 0
    slice_ = _month_slice(frame, month)
    mask = _nationwide_full_sample_mask(slice_)
    rows = slice_.loc[mask]
    count = int(len(rows))
    if count != 1:
        return None, count
    row = rows.iloc[0]
    violent = _finite_number(row.get("Violent Crime_mvs_12mo"))
    prop = _finite_number(row.get("Property Crime_mvs_12mo"))
    pop = _finite_number(row.get("FBI.Population.Covered"))
    if violent is None or prop is None or pop is None or pop <= 0:
        return None, count
    return float(round((violent + prop) / pop * 100000, 2)), count


def select_scored_incident_rate(frame) -> dict:
    """Population-weighted national rate for the latest calendar month.

    The RTCI Nationwide Full Sample row is the scored rate when it is the
    only such row for that month, its counts are usable, and its rate is
    within ``NATIONWIDE_RATE_TOLERANCE`` of the population-weighted total of
    the other usable rows. On the file the weekly job downloads, that row
    matches the weighted total exactly, including the agency crime and
    population totals, so 1.1.0 uses the row directly. It is the national
    figure RTCI publishes.

    If the row is missing, duplicated, unusable, or outside that tolerance,
    the scored rate is the population-weighted total of the other usable
    rows. A file with no Agency/State columns has no Nationwide row, so it
    takes this path. If the Nationwide row is the only usable row, it is
    used: nothing disagrees with it.

    Raises ``ValueError`` when the month cannot be parsed or no usable rate
    exists. Callers fail the fetch. They do not invent a rate or a date.
    """
    provenance = _provenance_from_frame(frame)
    month = provenance.get("value_month")
    month_end = provenance.get("value_month_end")
    if not month or not month_end:
        raise ValueError("crime file has no parseable month")

    nationwide_rate, nationwide_count = _nationwide_rate_for_month(frame, month)
    try:
        weighted = _rates_for_month(
            _without_nationwide_full_sample(frame), month
        )["population_weighted"]
    except ValueError:
        weighted = None

    if nationwide_rate is not None and (
        weighted is None or abs(nationwide_rate - weighted) <= NATIONWIDE_RATE_TOLERANCE
    ):
        source = RATE_SOURCE_NATIONWIDE
        scored = nationwide_rate
        if weighted is None:
            detail = (
                "RTCI Nationwide Full Sample row; no other usable rows to cross-check"
            )
        else:
            detail = (
                "RTCI Nationwide Full Sample row; it matches the population-weighted "
                "total of the other usable rows"
            )
    elif weighted is not None:
        source = RATE_SOURCE_WEIGHTED
        scored = weighted
        if nationwide_count == 0:
            detail = (
                "No Nationwide Full Sample row for the latest month; "
                "scored the population-weighted total of usable rows"
            )
        elif nationwide_count > 1:
            detail = (
                "More than one Nationwide Full Sample row for the latest month; "
                "scored the population-weighted total of the other usable rows"
            )
        elif nationwide_rate is None:
            detail = (
                "Nationwide Full Sample row was not usable; "
                "scored the population-weighted total of the other usable rows"
            )
        else:
            detail = (
                "Nationwide Full Sample rate disagreed with the population-weighted "
                "total; scored the weighted total"
            )
    else:
        raise ValueError(f"no usable national crime rate for {month}")

    return {
        "incident_rate": scored,
        "rate_source": source,
        "rate_source_detail": detail,
        "nationwide_full_sample_incident_rate": nationwide_rate,
        "population_weighted_excluding_nationwide": weighted,
        "observation_date": month_end,
    }


def crime_rate_diagnostics(frame) -> dict:
    """Rates for the latest calendar month, plus which one is scored.

    ``candidate_month`` and ``latest_month`` are both the latest calendar
    month in the file. The candidate used to be ``Date.max()``, a text sort,
    which reported September while April or December was already in the file.
    ``candidate_incident_rate`` is still the unweighted mean. It is not the
    1.1.0 input. ``scored_incident_rate`` is.
    """
    provenance = _provenance_from_frame(frame)
    candidate_month = provenance.get("value_month")
    if not candidate_month:
        raise ValueError("crime file has no parseable month")
    candidate = _rates_for_month(frame, candidate_month)
    selected = select_scored_incident_rate(frame)
    diagnostics = {
        "candidate_incident_rate": candidate["unweighted"],
        "candidate_month": candidate_month,
        "population_weighted_incident_rate": candidate["population_weighted"],
        "agencies": candidate["agencies"],
        "v1_0_0_locked_incident_rate": PUBLISHED_INCIDENT_RATE,
        "index_input": True,
        "scored_incident_rate": selected["incident_rate"],
        "rate_source": selected["rate_source"],
        "rate_source_detail": selected["rate_source_detail"],
        "nationwide_full_sample_incident_rate": selected["nationwide_full_sample_incident_rate"],
        "population_weighted_excluding_nationwide": selected[
            "population_weighted_excluding_nationwide"
        ],
        "latest_month": candidate_month,
        "latest_month_incident_rate": candidate["unweighted"],
        "latest_month_population_weighted_incident_rate": candidate["population_weighted"],
        "latest_month_agencies": candidate["agencies"],
    }
    return diagnostics


def _error(message: str) -> dict:
    return {"status": "error", "message": message, "data": {}}


def fetch(csv_text: Optional[str] = None, csv_path: Optional[str] = None):
    """
    Fetch the RTCI file and return the 1.1.0 national incident rate.

    With no arguments, download the cleaned file from the raw RTCI URL.
    Tests pass ``csv_text`` or ``csv_path`` and do not touch the network.

    An unreadable file, a non-CSV body (HTML included), or a latest month
    with no usable national rate returns ``status: error`` and no incident
    rate. It does not return success, and it does not invent an observation
    date. The weekly job treats that as a core failure and refuses to publish.
    """
    from runtime.util.download_crime_rate_data import (
        CrimeFileError,
        download_rtci_csv,
        read_rtci_csv,
        rtci_raw_csv_url,
    )

    source_url = rtci_raw_csv_url()
    try:
        if csv_text is None and csv_path is None:
            csv_text = download_rtci_csv()
        elif csv_text is None:
            try:
                with open(csv_path, encoding="utf-8-sig") as handle:
                    csv_text = handle.read()
            except OSError as exc:
                return _error(f"crime file unreadable: {exc}")
        frame = read_rtci_csv(csv_text)
        diagnostics = crime_rate_diagnostics(frame)
    except CrimeFileError as exc:
        return _error(str(exc))
    except ValueError as exc:
        return _error(f"crime file unreadable: {exc}")

    provenance = _provenance_from_frame(frame)
    provenance["source_url"] = source_url
    # The observation date is the last day of the month the scored rate
    # describes. period_end() builds it from a parsed calendar month.
    # fetched_at stays empty: this is a file vintage, not a clock time.
    observation_date = provenance.get("value_month_end")
    if not observation_date or diagnostics.get("scored_incident_rate") is None:
        return _error("crime file has no value-month end")
    return {
        "status": "success",
        "fetched_at": None,
        "observation_date": observation_date,
        "provenance": provenance,
        "diagnostics": diagnostics,
        "data": {
            "incident_rate": diagnostics["scored_incident_rate"],
        },
    }


if __name__ == "__main__":
    result = fetch()
    print(result)
