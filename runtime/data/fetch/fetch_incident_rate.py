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
from typing import Optional

"""
Fetcher for violent crime incident rate.

The published index input is locked at ``PUBLISHED_INCIDENT_RATE``. A weekly
run downloads the AH-Datalytics RTCI cleaned file, records its vintage, and
stores an unweighted candidate plus a population-weighted alternative as
diagnostics. Those diagnostics are not ``compute_index`` inputs. Replacing
2723.0 is a separate reviewed revision.
"""

# Resolve path relative to this file so it works from any CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.abspath(os.path.join(_HERE, ".."))

# v1.0.0 published crime input. Do not replace this from the RTCI file
# until a reviewed data revision says so.
PUBLISHED_INCIDENT_RATE = 2723.0

_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def crime_file_provenance(date_labels, last_updated) -> dict:
    """Dating for the local RTCI file. Does not choose the rate.

    ``value_month`` is the lexicographic maximum of the Date strings, which is
    the month ``DataFrame.max`` selects for the published rate. ``file_through``
    is the latest calendar month actually present in the file. Those differ
    when a later month sorts earlier as text (December before September).
    """
    labels = []
    for raw in date_labels:
        text = str(raw).strip()
        if text and text.lower() not in {"nan", "none"}:
            labels.append(text)
    if not labels:
        return {"kind": "file"}
    value_month = max(labels)
    file_through = max(labels, key=_chrono_key)
    updated = []
    for raw in last_updated:
        text = str(raw).strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            updated.append(text[:10])
    provenance = {
        "kind": "file",
        "value_month": value_month,
        "value_month_end": _month_end(value_month),
        "file_through": file_through,
    }
    if updated:
        provenance["file_updated"] = Counter(updated).most_common(1)[0][0]
    return provenance


def _chrono_key(label: str):
    parts = label.split()
    if len(parts) == 2 and parts[0] in _MONTHS and parts[1].isdigit():
        return (int(parts[1]), _MONTHS[parts[0]])
    return (0, 0)


def _month_end(label: str):
    parts = label.split()
    if len(parts) != 2 or parts[0] not in _MONTHS or not parts[1].isdigit():
        return None
    year = int(parts[1])
    month = _MONTHS[parts[0]]
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last:02d}"


def _rates_for_month(frame, month: str) -> dict:
    """Unweighted agency mean and population-weighted total for one month.

    Rows with a missing crime count or a non-positive population are left
    out of both figures so the two alternatives describe the same agencies.
    """
    import pandas as pd

    month_text = str(month).strip()
    dates = frame["Date"].astype(str).str.strip()
    slice_ = frame.loc[dates == month_text]
    violent = pd.to_numeric(slice_["Violent Crime_mvs_12mo"], errors="coerce")
    prop = pd.to_numeric(slice_["Property Crime_mvs_12mo"], errors="coerce")
    pop = pd.to_numeric(slice_["FBI.Population.Covered"], errors="coerce")
    total = violent + prop
    usable = total.notna() & pop.notna() & (pop > 0)
    if not bool(usable.any()):
        raise ValueError(f"no usable agency rows for {month_text}")
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

    ``candidate_incident_rate`` uses the same month rule as the locked
    series: the lexicographic maximum of ``Date`` (what ``DataFrame.max``
    selects). ``latest_month_*`` is the latest calendar month in the file,
    which can be newer than that lexicographic month.
    """
    provenance = crime_file_provenance(
        frame["Date"].tolist(),
        frame["Last Updated"].tolist() if "Last Updated" in frame.columns else [],
    )
    candidate_month = frame["Date"].max()
    candidate = _rates_for_month(frame, candidate_month)
    diagnostics = {
        "candidate_incident_rate": candidate["unweighted"],
        "candidate_month": str(candidate_month).strip(),
        "population_weighted_incident_rate": candidate["population_weighted"],
        "agencies": candidate["agencies"],
        "published_incident_rate": PUBLISHED_INCIDENT_RATE,
        "index_input": False,
    }
    file_through = provenance.get("file_through")
    if file_through:
        latest = _rates_for_month(frame, file_through)
        diagnostics["latest_month"] = file_through
        diagnostics["latest_month_incident_rate"] = latest["unweighted"]
        diagnostics["latest_month_population_weighted_incident_rate"] = latest["population_weighted"]
        diagnostics["latest_month_agencies"] = latest["agencies"]
    return diagnostics


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

    provenance = crime_file_provenance(
        frame["Date"].tolist(),
        frame["Last Updated"].tolist() if "Last Updated" in frame.columns else [],
    )
    provenance["source_url"] = source_url
    # No observation timestamp: the rate's vintage is the file month.
    # The locked number below is the index input. Diagnostics are not.
    return {
        "status": "success",
        "fetched_at": None,
        "provenance": provenance,
        "diagnostics": diagnostics,
        "data": {
            "incident_rate": PUBLISHED_INCIDENT_RATE,
        },
    }


if __name__ == "__main__":
    result = fetch()
    print(result)
