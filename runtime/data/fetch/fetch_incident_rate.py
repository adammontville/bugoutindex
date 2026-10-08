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
Fetcher for violent crime incident rate.

The published index input is locked at ``PUBLISHED_INCIDENT_RATE``. A weekly
run downloads the AH-Datalytics RTCI cleaned file, records its vintage, and
stores an unweighted candidate plus a population-weighted alternative as
diagnostics. Those diagnostics are not ``compute_index`` inputs. Replacing
2723.0 is a separate reviewed revision.

The candidate month is the latest calendar month in the file. RTCI writes
``Date`` as a month name (``format(as.Date(date), "%B %Y")`` in
``final_sample_to_viz.R``) and also writes numeric ``Month`` and ``Year``.
Sorting the ``Date`` text picks September over April and over December.
The month is parsed instead.
"""

# Resolve path relative to this file so it works from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))

# v1.0.0 published crime input. Do not replace this from the RTCI file
# until a reviewed data revision says so.
PUBLISHED_INCIDENT_RATE = 2723.0

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
    in the mean. That inclusion is the construction behind the locked 2723.0
    print (399 usable rows on the old local file) and the current diagnostics
    (621 usable rows). Dropping the aggregate rows would change both numbers.
    This function does not drop them.

    The population-weighted alternative is the sum of crimes divided by the
    sum of population on the same rows. On the cleaned file that figure
    matches the Nationwide Full Sample row. It is diagnostic only.

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


def crime_rate_diagnostics(frame) -> dict:
    """Candidate rates from an RTCI frame. Not an index input.

    ``candidate_month`` and ``latest_month`` are both the latest calendar
    month in the file. The candidate used to be ``Date.max()``, a text sort,
    which reported September while April or December was already in the file.
    """
    provenance = _provenance_from_frame(frame)
    candidate_month = provenance.get("value_month")
    if not candidate_month:
        raise ValueError("crime file has no parseable month")
    candidate = _rates_for_month(frame, candidate_month)
    diagnostics = {
        "candidate_incident_rate": candidate["unweighted"],
        "candidate_month": candidate_month,
        "population_weighted_incident_rate": candidate["population_weighted"],
        "agencies": candidate["agencies"],
        "published_incident_rate": PUBLISHED_INCIDENT_RATE,
        "index_input": False,
        "latest_month": candidate_month,
        "latest_month_incident_rate": candidate["unweighted"],
        "latest_month_population_weighted_incident_rate": candidate["population_weighted"],
        "latest_month_agencies": candidate["agencies"],
    }
    return diagnostics


def locked_rate_observation_date(candidate_rate, value_month_end):
    """Month-end of the locked rate, or None when this file's latest month is not that rate.

    ``candidate_rate`` is the unweighted mean for the latest calendar month.
    The published input stays ``PUBLISHED_INCIDENT_RATE``. A newer month in
    the file moves the candidate without changing 2723.0. That month-end is
    file vintage, not an observation date for the locked rate, unless the
    candidate is still 2723.0.
    """
    try:
        candidate = float(candidate_rate)
    except (TypeError, ValueError):
        return None
    locked = float(PUBLISHED_INCIDENT_RATE)
    if abs(candidate - locked) > 1e-6 * max(1.0, abs(locked)):
        return None
    return value_month_end


def _error(message: str) -> dict:
    return {"status": "error", "message": message, "data": {}}


def fetch(csv_text: Optional[str] = None, csv_path: Optional[str] = None):
    """
    Fetch RTCI diagnostics and return the locked published incident rate.

    With no arguments, download the cleaned file from the raw RTCI URL.
    Tests pass ``csv_text`` or ``csv_path`` and do not touch the network.

    An unreadable file or a non-CSV body (HTML included) returns
    ``status: error`` and no incident rate. It does not return success.
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
    # Observation date is the last day of the month the locked rate describes.
    # That is the latest calendar month's end only when that month's
    # unweighted rate is still 2723.0. Diagnostics are not the index input.
    # fetched_at stays empty: this is a file vintage, not a clock time.
    return {
        "status": "success",
        "fetched_at": None,
        "observation_date": locked_rate_observation_date(
            diagnostics.get("candidate_incident_rate"),
            provenance.get("value_month_end"),
        ),
        "provenance": provenance,
        "diagnostics": diagnostics,
        "data": {
            "incident_rate": PUBLISHED_INCIDENT_RATE,
        },
    }


if __name__ == "__main__":
    result = fetch()
    print(result)
