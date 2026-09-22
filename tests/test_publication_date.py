# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""publication_date follows America/Chicago, and a refusal does not publish."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from runtime.publish.failure_notice import (
    EXIT_CORE_REFUSED,
    EXIT_MARKETS_OR_PULSE_REFUSED,
    describe_publish_failure,
    describe_publish_failure_oneline,
)
from runtime.publish.weekly_run import publication_date_for

ROOT = Path(__file__).resolve().parents[1]


def test_utc_saturday_just_after_midnight_is_chicago_friday():
    # September 2026 is CDT (UTC-5). 00:09 UTC Saturday is 19:09 Friday Chicago.
    # This is the delayed-start case: cron is 23:30 UTC Friday, GitHub starts later.
    instant = datetime(2026, 9, 19, 0, 9, tzinfo=timezone.utc)
    stamped = publication_date_for(instant)
    assert stamped == "2026-09-18"
    assert date.fromisoformat(stamped).strftime("%A") == "Friday"
    assert instant.strftime("%A") == "Saturday"


def test_observed_september_delay_stays_friday():
    # Roadmap: September 2026 runs started around 01:09–01:21 UTC Saturday.
    instant = datetime(2026, 9, 19, 1, 15, tzinfo=timezone.utc)
    stamped = publication_date_for(instant)
    assert stamped == "2026-09-18"
    assert date.fromisoformat(stamped).strftime("%A") == "Friday"


def test_on_time_friday_cron_stays_friday():
    # 23:30 UTC Friday is 18:30 CDT.
    stamped = publication_date_for(datetime(2026, 9, 18, 23, 30, tzinfo=timezone.utc))
    assert stamped == "2026-09-18"
    assert date.fromisoformat(stamped).strftime("%A") == "Friday"


def test_winter_delay_is_friday_until_chicago_midnight():
    # January is CST (UTC-6). 05:59 UTC Saturday is 23:59 Friday Chicago.
    late = publication_date_for(datetime(2026, 1, 10, 5, 59, tzinfo=timezone.utc))
    assert late == "2026-01-09"
    assert date.fromisoformat(late).strftime("%A") == "Friday"
    after = publication_date_for(datetime(2026, 1, 10, 6, 0, tzinfo=timezone.utc))
    assert after == "2026-01-10"
    assert date.fromisoformat(after).strftime("%A") == "Saturday"


def test_naive_clock_is_treated_as_utc():
    stamped = publication_date_for(datetime(2026, 9, 19, 1, 15))
    assert stamped == "2026-09-18"


def test_readme_quotes_the_workflow_cron():
    workflow = (ROOT / ".github/workflows/weekly-update.yml").read_text()
    readme = (ROOT / "runtime/publish/README.md").read_text()
    match = re.search(r'cron:\s*"([^"]+)"', workflow)
    assert match is not None
    cron = match.group(1)
    assert cron == "30 23 * * 5"
    assert f"`{cron}`" in readme
    assert "22:00 America/Chicago" not in readme
    assert "03:00 UTC Saturday" not in readme


def test_failure_summary_distinguishes_refuse_and_crash():
    core = describe_publish_failure(EXIT_CORE_REFUSED)
    assert "Refused (exit 2)" in core
    assert "core metric" in core
    assert "live site was not updated" in core.lower()

    feeds = describe_publish_failure(EXIT_MARKETS_OR_PULSE_REFUSED)
    assert "Refused (exit 3)" in feeds
    assert "Markets or the short-term pulse" in feeds

    crash = describe_publish_failure(1)
    assert "Crashed (exit 1)" in crash
    assert "exit 2 or 3" in crash

    oneline = describe_publish_failure_oneline(2)
    assert "\n" not in oneline
    assert "Refused (exit 2)" in oneline
    assert "Live site unchanged" in oneline


def test_core_refusal_does_not_write_a_snapshot(tmp_path, monkeypatch):
    import runtime.publish.weekly_run as weekly

    monkeypatch.setattr(weekly, "DOCS_DATA", tmp_path / "docs")
    monkeypatch.setattr(weekly, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(
        weekly,
        "fetch_core_metrics",
        lambda: {metric: {"status": "error", "data": {}} for metric in weekly.CORE_METRICS},
    )

    def _should_not_fetch():
        raise AssertionError("markets fetch ran after a core refusal")

    monkeypatch.setattr(weekly, "fetch_markets", _should_not_fetch)
    assert weekly.main() == EXIT_CORE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()
    assert not (tmp_path / "data").exists()


def test_markets_refusal_does_not_write_a_snapshot(tmp_path, monkeypatch):
    import runtime.publish.weekly_run as weekly

    monkeypatch.setattr(weekly, "DOCS_DATA", tmp_path / "docs")
    monkeypatch.setattr(weekly, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(
        weekly,
        "fetch_core_metrics",
        lambda: {
            metric: {"status": "success", "data": {metric: 1.0}, "fetched_at": "2026-09-01"}
            for metric in weekly.CORE_METRICS
        },
    )
    monkeypatch.setattr(weekly, "fetch_markets", lambda: {"status": "error", "data": {}})
    monkeypatch.setattr(weekly, "fetch_pulse", lambda: {"status": "success", "data": {}})
    monkeypatch.setattr(weekly, "fetch_revisions", lambda: {"status": "success"})

    assert weekly.main() == EXIT_MARKETS_OR_PULSE_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()
    assert not (tmp_path / "data" / "weekly_bugout_index.csv").exists()


def test_failure_notice_cli_prints_summary(capsys):
    from runtime.publish.failure_notice import main

    assert main(["3"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("## Weekly publish failed")
    assert "Refused (exit 3)" in out

    assert main(["--oneline", "2"]) == 0
    line = capsys.readouterr().out.strip()
    assert "\n" not in line
    assert line.startswith("Refused (exit 2)")
