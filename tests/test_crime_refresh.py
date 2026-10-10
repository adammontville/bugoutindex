# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""RTCI download, fail-closed parse, and the 1.1.0 national crime rate."""
from __future__ import annotations

from runtime.data.fetch.fetch_incident_rate import (
    PUBLISHED_INCIDENT_RATE,
    RATE_SOURCE_NATIONWIDE,
    RATE_SOURCE_WEIGHTED,
    crime_file_provenance,
    fetch as fetch_incident_rate,
)
from runtime.processing.formula import METRIC_RANGES, WEIGHTS, interpret
from runtime.publish.observation_dates import observation_date_for
from runtime.publish.weekly_run import build_snapshot, compute_index, core_history_row
from runtime.util.download_crime_rate_data import (
    CrimeFileError,
    body_is_html,
    download_rtci_csv,
    read_rtci_csv,
    rtci_raw_csv_url,
)

# 19 September 2026 published inputs. Crime in that week is the 1.0.0 lock.
# Tests that call the fetcher replace incident_rate with the file's rate.
PUBLISHED_RAWS = {
    "inflation_rate": 3.353016322755652,
    "incident_rate": 2723.0,
    "unemployment_rate": 4.1,
    "debt_to_gdp_ratio": 122.59387,
    "homelessness_rate": 0.23,
    "trust_in_government": 41.0,
}

# "September" sorts after "April" and "December" as text. The latest
# calendar month in this file is April 2026.
FIXTURE_CSV = """\
Date,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
September 2024,100,100,10000,2026-06-16 12:00:00 EST
September 2024,10,10,100000,2026-06-16 12:00:00 EST
September 2024,1,1,NA,2026-06-16 12:00:00 EST
December 2024,50,50,10000,2026-06-16 12:00:00 EST
April 2026,40,60,20000,2026-06-16 12:00:00 EST
"""

HTML_BODY = """\
<!DOCTYPE html>
<html><head><title>final_sample.csv</title></head>
<body>GitHub blob page, not a CSV</body></html>
"""


def test_raw_url_is_the_cleaned_file_on_main():
    url = rtci_raw_csv_url()
    assert url == (
        "https://raw.githubusercontent.com/AH-Datalytics/rtci/main/docs/app_data/final_sample.csv"
    )
    assert "/blob/" not in url
    assert "jacobkap" not in url
    assert "development" not in url
    assert url.startswith("https://raw.githubusercontent.com/")


def test_fixture_csv_parses_and_records_vintage():
    frame = read_rtci_csv(FIXTURE_CSV)
    assert list(frame["Date"].astype(str))[0] == "September 2024"
    payload = fetch_incident_rate(csv_text=FIXTURE_CSV)
    assert payload["status"] == "success"
    provenance = payload["provenance"]
    assert provenance["kind"] == "file"
    assert provenance["value_month"] == "April 2026"
    assert provenance["value_month_end"] == "2026-04-30"
    assert provenance["file_through"] == "April 2026"
    assert provenance["file_updated"] == "2026-06-16"
    assert "/blob/" not in provenance["source_url"]
    diagnostics = payload["diagnostics"]
    # 100 crimes / 20000 people * 100000 = 500. September's 1010 is not the candidate.
    assert diagnostics["candidate_incident_rate"] == 500.0
    assert diagnostics["candidate_month"] == "April 2026"
    assert diagnostics["population_weighted_incident_rate"] == 500.0
    assert diagnostics["agencies"] == 1
    assert diagnostics["latest_month"] == "April 2026"
    assert diagnostics["latest_month_incident_rate"] == 500.0
    assert diagnostics["latest_month_population_weighted_incident_rate"] == 500.0
    assert diagnostics["index_input"] is True
    assert diagnostics["v1_0_0_locked_incident_rate"] == PUBLISHED_INCIDENT_RATE
    assert "published_incident_rate" not in diagnostics
    # No Agency/State columns, so there is no Nationwide row. The scored
    # rate is the weighted total, which is this one usable row.
    assert diagnostics["rate_source"] == RATE_SOURCE_WEIGHTED
    assert diagnostics["scored_incident_rate"] == 500.0
    assert diagnostics["nationwide_full_sample_incident_rate"] is None
    assert payload["data"]["incident_rate"] == 500.0
    assert payload["observation_date"] == "2026-04-30"
    assert observation_date_for("incident_rate", payload) == "2026-04-30"


def test_html_body_is_not_a_successful_fetch():
    assert body_is_html(HTML_BODY, "text/html")
    try:
        read_rtci_csv(HTML_BODY, "text/html")
    except CrimeFileError as exc:
        assert "HTML" in str(exc)
    else:
        raise AssertionError("HTML body was parsed as CSV")

    payload = fetch_incident_rate(csv_text=HTML_BODY)
    assert payload["status"] == "error"
    assert payload["status"] != "success"
    assert "incident_rate" not in (payload.get("data") or {})
    assert "diagnostics" not in payload
    assert payload.get("observation_date") is None

    def getter(url):
        assert url == rtci_raw_csv_url()
        return HTML_BODY, "text/html; charset=utf-8"

    try:
        download_rtci_csv(getter=getter)
    except CrimeFileError as exc:
        assert "HTML" in str(exc)
    else:
        raise AssertionError("HTML download was returned as CSV")


def test_blob_url_is_refused_before_any_save():
    called = {"n": 0}

    def getter(url):
        called["n"] += 1
        return FIXTURE_CSV, "text/plain"

    blob = "https://github.com/AH-Datalytics/rtci/blob/development/data/final_sample.csv"
    try:
        download_rtci_csv(url=blob, getter=getter)
    except CrimeFileError as exc:
        assert "blob" in str(exc)
    else:
        raise AssertionError("blob URL was accepted")
    assert called["n"] == 0


def test_download_getter_receives_the_raw_url_and_parses():
    seen = {}

    def getter(url):
        seen["url"] = url
        return FIXTURE_CSV, "text/plain"

    text = download_rtci_csv(getter=getter)
    assert seen["url"] == rtci_raw_csv_url()
    assert text.splitlines()[0].startswith("Date,")
    frame = read_rtci_csv(text)
    assert len(frame) == 5


def test_unreadable_and_non_csv_fail_closed(tmp_path):
    missing = fetch_incident_rate(csv_path=str(tmp_path / "no-such.csv"))
    assert missing["status"] == "error"
    assert "incident_rate" not in missing["data"]

    junk = tmp_path / "notes.txt"
    junk.write_text("this is not a csv\njust a sentence\n", encoding="utf-8")
    payload = fetch_incident_rate(csv_path=str(junk))
    assert payload["status"] == "error"
    assert "incident_rate" not in (payload.get("data") or {})

    broken = "Date,Something Else\nSeptember 2024,1\n"
    assert fetch_incident_rate(csv_text=broken)["status"] == "error"


# A later September sorts after September 2024 as text, so Date.max() moves
# even though the locked rate is still the older month's 2723.
LATER_SEPTEMBER_CSV = """\
Date,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
September 2024,200,72.3,10000,2026-06-16 12:00:00 EST
September 2025,10,10,10000,2026-06-16 12:00:00 EST
"""


def test_later_month_dates_the_scored_rate_not_the_v1_lock():
    crime = fetch_incident_rate(csv_text=LATER_SEPTEMBER_CSV)
    assert crime["status"] == "success"
    assert crime["data"]["incident_rate"] == 200.0
    assert crime["data"]["incident_rate"] != PUBLISHED_INCIDENT_RATE
    assert crime["provenance"]["value_month"] == "September 2025"
    assert crime["provenance"]["value_month_end"] == "2025-09-30"
    assert crime["diagnostics"]["candidate_incident_rate"] == 200.0
    assert crime["diagnostics"]["candidate_month"] == "September 2025"
    assert crime["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED
    assert crime["observation_date"] == "2025-09-30"
    assert observation_date_for("incident_rate", crime) == "2025-09-30"
    # A blank date on a file payload is still not filled from the vintage.
    # That is how 1.0.0 rows keep 2723.0 undated.
    undated = dict(crime, observation_date=None)
    assert observation_date_for("incident_rate", undated) is None

    results = {
        metric: {"status": "success", "data": {metric: raw}}
        for metric, raw in PUBLISHED_RAWS.items()
    }
    results["incident_rate"] = crime
    scored = compute_index(results)
    assert scored["index"] != 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 200.0
    row = core_history_row("2026-10-02", scored, results)
    assert row["incident_rate"] == 200.0
    assert row["incident_rate_observation_date"] == "2025-09-30"


def test_weighted_rate_is_the_index_input_and_the_snapshot_stamps_1_1_0():
    crime = fetch_incident_rate(csv_text=FIXTURE_CSV)
    assert crime["data"]["incident_rate"] == 500.0
    assert crime["diagnostics"]["candidate_incident_rate"] == 500.0
    assert crime["diagnostics"]["candidate_incident_rate"] != PUBLISHED_INCIDENT_RATE

    results = {
        metric: {"status": "success", "data": {metric: raw}}
        for metric, raw in PUBLISHED_RAWS.items()
    }
    results["incident_rate"] = crime
    scored = compute_index(results)
    assert scored["index"] == 62.05
    assert scored["metrics"]["incident_rate"]["raw"] == 500.0
    assert scored["metrics"]["incident_rate"]["weight"] == 0.12
    assert "candidate_incident_rate" not in scored["metrics"]["incident_rate"]

    snapshot = build_snapshot(
        "2026-09-19",
        scored,
        results,
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
    )
    assert snapshot["schema_version"] == 1
    assert snapshot["methodology_version"] == "1.1.0"
    assert snapshot["bugout_index"] == 62.05
    block = snapshot["metrics"]["incident_rate"]
    assert block["raw"] == 500.0
    assert block["diagnostics"]["candidate_incident_rate"] == 500.0
    assert block["diagnostics"]["candidate_month"] == "April 2026"
    assert block["diagnostics"]["population_weighted_incident_rate"] == 500.0
    assert block["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED
    assert block["diagnostics"]["index_input"] is True
    assert block["provenance"]["value_month"] == "April 2026"
    assert block["provenance"]["file_through"] == "April 2026"
    assert block["observation_date"] == "2026-04-30"
    assert block["status"] == "success"


def test_month_names_order_by_calendar_across_years():
    """September sorts after April and December as text. The calendar does not."""
    labels = [
        "September 2024",
        "December 2024",
        "January 2025",
        "September 2025",
        "April 2026",
    ]
    provenance = crime_file_provenance(labels, [])
    assert provenance["value_month"] == "April 2026"
    assert provenance["file_through"] == "April 2026"
    assert provenance["value_month_end"] == "2026-04-30"
    # The original lock: September 2024 wins a text sort over December 2024.
    old_file = crime_file_provenance(
        ["September 2024", "December 2024", "January 2024"],
        [],
    )
    assert old_file["value_month"] == "December 2024"
    assert old_file["value_month_end"] == "2024-12-31"
    assert max(labels) == "September 2025"


def test_date_formats_resolve_to_the_same_calendar_month():
    cases = [
        (["2025-09-01", "2026-04-15", "2024-12-01"], "April 2026"),
        (["2025-09", "2026-04", "2024-12"], "April 2026"),
        (["Sep 2025", "Apr 2026", "Dec 2024"], "April 2026"),
        (["09/2025", "4/2026", "12/2024"], "April 2026"),
        (["2025/09/01", "2026/04/01"], "April 2026"),
        (["September, 2025", "April, 2026"], "April 2026"),
        (["30 September 2025", "15 April 2026"], "April 2026"),
    ]
    for labels, expected in cases:
        found = crime_file_provenance(labels, [])
        assert found["value_month"] == expected, labels
        assert found["file_through"] == expected


def test_month_and_year_columns_beat_a_misleading_date_string():
    csv_text = """\
Month,Year,Date,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
9,2025,September 2025,10,10,10000,2026-06-16 12:00:00 EST
4,2026,September 2025,40,60,20000,2026-06-16 12:00:00 EST
"""
    payload = fetch_incident_rate(csv_text=csv_text)
    assert payload["status"] == "success"
    assert payload["provenance"]["value_month"] == "April 2026"
    assert payload["diagnostics"]["candidate_month"] == "April 2026"
    assert payload["diagnostics"]["candidate_incident_rate"] == 500.0
    assert payload["diagnostics"]["latest_month"] == "April 2026"
    assert payload["data"]["incident_rate"] == 500.0
    assert payload["observation_date"] == "2026-04-30"
    assert payload["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED


def test_iso_dates_pick_april_over_september():
    csv_text = """\
Date,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
2025-09-01,10,10,10000,2026-06-16 12:00:00 EST
2026-04-01,40,60,20000,2026-06-16 12:00:00 EST
2024-12-01,1,1,10000,2026-06-16 12:00:00 EST
"""
    payload = fetch_incident_rate(csv_text=csv_text)
    assert payload["diagnostics"]["candidate_month"] == "April 2026"
    assert payload["diagnostics"]["latest_month_incident_rate"] == 500.0
    assert payload["provenance"]["value_month_end"] == "2026-04-30"


# April 2026's one usable row is 2723. September 2025 sorts later as text.
LATEST_MONTH_CSV = """\
Date,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
September 2025,10,10,10000,2026-06-16 12:00:00 EST
April 2026,200,72.3,10000,2026-06-16 12:00:00 EST
"""


def test_observation_date_is_the_latest_month_end_from_the_file():
    crime = fetch_incident_rate(csv_text=LATEST_MONTH_CSV)
    assert crime["data"]["incident_rate"] == 2723.0
    assert crime["diagnostics"]["candidate_month"] == "April 2026"
    assert crime["diagnostics"]["candidate_incident_rate"] == 2723.0
    assert crime["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED
    assert crime["observation_date"] == "2026-04-30"
    assert crime["observation_date"] != "2026-06-16"
    assert observation_date_for("incident_rate", crime) == "2026-04-30"
    mismatched = dict(crime, observation_date="2025-09-30")
    assert observation_date_for("incident_rate", mismatched) is None

    results = {
        metric: {"status": "success", "data": {metric: raw}}
        for metric, raw in PUBLISHED_RAWS.items()
    }
    results["incident_rate"] = crime
    scored = compute_index(results)
    assert scored["index"] == 57.11
    row = core_history_row("2026-10-02", scored, results)
    assert row["incident_rate"] == 2723.0
    assert row["incident_rate_observation_date"] == "2026-04-30"


# Two agencies plus the RTCI Nationwide Full Sample row. The unweighted mean
# of the three rows is not the national rate. The row matches the weighted
# total of the agencies, so it is the scored input.
NATIONWIDE_CSV = """\
Month,Year,Date,Agency,State,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated,Source.Type
4,2026,April 2026,Smallville,TX,100,100,10000,2026-06-16 12:00:00 EST,State UCR
4,2026,April 2026,Bigville,TX,50,50,90000,2026-06-16 12:00:00 EST,State UCR
4,2026,April 2026,Full Sample,Nationwide,150,150,100000,2026-06-16 12:00:00 EST,Aggregate
9,2025,September 2025,Smallville,TX,10,10,10000,2026-06-16 12:00:00 EST,State UCR
"""

# The Nationwide row is not the agency total. The weighted total is scored.
DISAGREE_CSV = """\
Month,Year,Date,Agency,State,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
4,2026,April 2026,Smallville,TX,100,100,10000,2026-06-16 12:00:00 EST
4,2026,April 2026,Bigville,TX,50,50,90000,2026-06-16 12:00:00 EST
4,2026,April 2026,Full Sample,Nationwide,5000,5000,10000,2026-06-16 12:00:00 EST
"""

DUPLICATE_NATIONWIDE_CSV = """\
Month,Year,Date,Agency,State,Violent Crime_mvs_12mo,Property Crime_mvs_12mo,FBI.Population.Covered,Last Updated
4,2026,April 2026,Smallville,TX,100,100,10000,2026-06-16 12:00:00 EST
4,2026,April 2026,Full Sample,Nationwide,100,100,10000,2026-06-16 12:00:00 EST
4,2026,April 2026,Full Sample,Nationwide,100,100,10000,2026-06-16 12:00:00 EST
"""


def test_nationwide_full_sample_is_scored_when_it_matches_the_weighted_total():
    crime = fetch_incident_rate(csv_text=NATIONWIDE_CSV)
    assert crime["status"] == "success"
    # Agencies: 200 crimes / 100000 people * 100000 = 200. The row is that total.
    assert crime["data"]["incident_rate"] == 300.0
    assert crime["diagnostics"]["rate_source"] == RATE_SOURCE_NATIONWIDE
    assert crime["diagnostics"]["nationwide_full_sample_incident_rate"] == 300.0
    assert crime["diagnostics"]["population_weighted_excluding_nationwide"] == 300.0
    assert crime["diagnostics"]["candidate_incident_rate"] != 300.0
    assert crime["diagnostics"]["index_input"] is True
    assert crime["observation_date"] == "2026-04-30"
    assert crime["provenance"]["value_month"] == "April 2026"
    assert "matches the population-weighted" in crime["diagnostics"]["rate_source_detail"]
    assert METRIC_RANGES["incident_rate"] == (500, 8000)
    assert WEIGHTS["incident_rate"] == 0.12


def test_weighted_total_is_scored_when_the_nationwide_row_disagrees():
    crime = fetch_incident_rate(csv_text=DISAGREE_CSV)
    assert crime["status"] == "success"
    assert crime["diagnostics"]["nationwide_full_sample_incident_rate"] == 100000.0
    assert crime["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED
    assert crime["data"]["incident_rate"] == 300.0
    assert crime["observation_date"] == "2026-04-30"
    assert "disagreed" in crime["diagnostics"]["rate_source_detail"]


def test_duplicate_nationwide_rows_fall_back_to_the_weighted_total():
    crime = fetch_incident_rate(csv_text=DUPLICATE_NATIONWIDE_CSV)
    assert crime["status"] == "success"
    assert crime["diagnostics"]["nationwide_full_sample_incident_rate"] is None
    assert crime["diagnostics"]["rate_source"] == RATE_SOURCE_WEIGHTED
    assert "More than one Nationwide Full Sample row" in crime["diagnostics"]["rate_source_detail"]
    # The two duplicate rows are excluded. The remaining agency row is 2000.
    assert crime["data"]["incident_rate"] == 2000.0
    assert crime["observation_date"] == "2026-04-30"


def test_october_2026_basket_projects_to_57_66_without_rewriting_history():
    """The 2026-10-02 week stays at 57.04. The 2026-10-09 publish is that projection."""
    import csv
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    latest = json.loads((root / "docs" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["methodology_version"] == "1.1.0"
    assert latest["schema_version"] == 1
    assert latest["bugout_index"] == 57.66
    assert latest["publication_date"] == "2026-10-09"
    assert latest["metrics"]["incident_rate"]["raw"] == 2443.27
    assert latest["metrics"]["incident_rate"]["observation_date"] == "2026-04-30"

    weekly = root / "runtime" / "data" / "weekly_bugout_index.csv"
    with weekly.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    published = next(row for row in rows if row["date"] == "2026-10-02")
    assert float(published["incident_rate"]) == 2723.0
    assert published["incident_rate_observation_date"] in ("", None)
    assert float(published["bugout_index"]) == 57.04

    fixture = root / "runtime" / "backtest" / "fixtures" / "v2" / "RTCI_monthly.csv"
    with fixture.open(newline="", encoding="utf-8") as handle:
        april = next(
            row for row in csv.DictReader(handle) if row["observation_date"] == "2026-04-01"
        )
    weighted = float(april["incident_rate_population_weighted"])
    assert weighted == 2443.27

    raws = {
        "inflation_rate": float(published["inflation_rate"]),
        "incident_rate": weighted,
        "unemployment_rate": float(published["unemployment_rate"]),
        "debt_to_gdp_ratio": float(published["debt_to_gdp_ratio"]),
        "homelessness_rate": float(published["homelessness_rate"]),
        "trust_in_government": float(published["trust_in_government"]),
    }
    scored = compute_index({metric: {"data": {metric: value}} for metric, value in raws.items()})
    assert scored["index"] == 57.66
    assert scored["metrics"]["incident_rate"]["normalized"] == 74.09
    assert scored["metrics"]["incident_rate"]["weight"] == 0.12
    assert interpret(scored["index"])["band"] == "Moderate Stability"
    assert METRIC_RANGES["incident_rate"] == (500, 8000)
