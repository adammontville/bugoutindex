# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""RTCI download, fail-closed parse, and locked crime input."""
from __future__ import annotations

from runtime.data.fetch.fetch_incident_rate import (
    PUBLISHED_INCIDENT_RATE,
    fetch as fetch_incident_rate,
)
from runtime.publish.weekly_run import build_snapshot, compute_index
from runtime.util.download_crime_rate_data import (
    CrimeFileError,
    body_is_html,
    download_rtci_csv,
    read_rtci_csv,
    rtci_raw_csv_url,
)

# 19 September 2026 published inputs. Crime stays 2723.0.
PUBLISHED_RAWS = {
    "inflation_rate": 3.353016322755652,
    "incident_rate": 2723.0,
    "unemployment_rate": 4.1,
    "debt_to_gdp_ratio": 122.59387,
    "homelessness_rate": 0.23,
    "trust_in_government": 41.0,
}

# September sorts after April and December as text, so Date.max() is
# September 2024. The latest calendar month is April 2026.
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
    assert provenance["value_month"] == "September 2024"
    assert provenance["file_through"] == "April 2026"
    assert provenance["file_updated"] == "2026-06-16"
    assert "/blob/" not in provenance["source_url"]
    diagnostics = payload["diagnostics"]
    # (200/10000 + 20/100000) / 2 * 100000 = 1010; the NA population row is out.
    assert diagnostics["candidate_incident_rate"] == 1010.0
    assert diagnostics["candidate_month"] == "September 2024"
    # 220 crimes / 110000 people * 100000 = 200.
    assert diagnostics["population_weighted_incident_rate"] == 200.0
    assert diagnostics["latest_month"] == "April 2026"
    assert diagnostics["latest_month_incident_rate"] == 500.0
    assert diagnostics["index_input"] is False
    assert diagnostics["published_incident_rate"] == PUBLISHED_INCIDENT_RATE


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


def test_diagnostics_do_not_change_the_locked_score():
    crime = fetch_incident_rate(csv_text=FIXTURE_CSV)
    assert crime["data"]["incident_rate"] == 2723.0
    assert crime["diagnostics"]["candidate_incident_rate"] != 2723.0

    results = {
        metric: {"status": "success", "data": {metric: raw}}
        for metric, raw in PUBLISHED_RAWS.items()
    }
    results["incident_rate"] = crime
    scored = compute_index(results)
    assert scored["index"] == 57.11
    assert scored["metrics"]["incident_rate"]["raw"] == 2723.0
    assert "candidate_incident_rate" not in scored["metrics"]["incident_rate"]

    snapshot = build_snapshot(
        "2026-09-19",
        scored,
        results,
        {"status": "success", "data": {}},
        {"data": {}, "dates": {}},
    )
    assert snapshot["bugout_index"] == 57.11
    block = snapshot["metrics"]["incident_rate"]
    assert block["raw"] == 2723.0
    assert block["diagnostics"]["candidate_incident_rate"] == 1010.0
    assert block["diagnostics"]["population_weighted_incident_rate"] == 200.0
    assert block["diagnostics"]["index_input"] is False
    assert block["provenance"]["file_through"] == "April 2026"
    assert block["status"] == "success"
