# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Schema 1 matches docs/data/latest.json, and the weekly job does not import Streamlit."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from runtime.processing.formula import CORE_METRICS
from runtime.publish.failure_notice import (
    EXIT_SNAPSHOT_REFUSED,
    describe_publish_failure,
)
from runtime.publish.snapshot_schema import (
    COMPANION_BLOCKS,
    HISTORY_SERIES,
    ACCEPTED_METHODOLOGY_VERSIONS,
    METHODOLOGY_VERSION,
    REQUIRED_TOP_LEVEL,
    SCHEMA_VERSION,
    SHADOW_BLOCKS,
    validate_published_snapshot,
)
from runtime.util.secrets_compat import get_secret
from runtime.viewer_io import load_published_snapshot

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
PUBLISH_SCAN = (
    ROOT / "runtime" / "publish",
    ROOT / "runtime" / "data" / "fetch",
    ROOT / "runtime" / "processing",
    ROOT / "runtime" / "backtest",
)


def _imports_streamlit(text: str) -> bool:
    return "import streamlit" in text or "from streamlit" in text


def test_live_snapshot_matches_schema_1_and_the_score_is_unchanged():
    raw = json.loads(LATEST.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["methodology_version"] == "1.1.0"
    assert raw["bugout_index"] == 57.66
    assert raw["metrics"]["incident_rate"]["raw"] == 2443.27
    assert SCHEMA_VERSION == 1
    assert METHODOLOGY_VERSION == "1.1.0"
    assert ACCEPTED_METHODOLOGY_VERSIONS == ("1.0.0", "1.1.0")
    assert list(CORE_METRICS) == [
        "inflation_rate",
        "incident_rate",
        "unemployment_rate",
        "debt_to_gdp_ratio",
        "homelessness_rate",
        "trust_in_government",
    ]
    assert validate_published_snapshot(raw) == []
    assert set(REQUIRED_TOP_LEVEL) == set(raw)
    assert set(HISTORY_SERIES) == set(raw["history"])
    for name in SHADOW_BLOCKS:
        assert raw[name]["in_bugout_index"] is False
    for name in COMPANION_BLOCKS:
        assert name not in raw["metrics"]
    loaded = load_published_snapshot()
    assert loaded["bugout_index"] == 57.66
    assert loaded["publication_date"] == raw["publication_date"]


def test_schema_rejects_a_shape_change_a_folded_companion_and_a_secret():
    snapshot = json.loads(LATEST.read_text(encoding="utf-8"))

    missing = copy.deepcopy(snapshot)
    del missing["metrics"]["homelessness_rate"]
    assert any("metrics must be the six cores" in item for item in validate_published_snapshot(missing))

    folded = copy.deepcopy(snapshot)
    folded["labor_shadow"]["in_bugout_index"] = True
    assert any("in_bugout_index" in item for item in validate_published_snapshot(folded))

    extra = copy.deepcopy(snapshot)
    extra["new_companion"] = {"in_bugout_index": False}
    assert any("unexpected top-level" in item for item in validate_published_snapshot(extra))

    leaked = copy.deepcopy(snapshot)
    leaked["pulse"]["note"] = "upstream said api_key=abcdefghijklmnop"
    assert any("secret" in item for item in validate_published_snapshot(leaked))

    current = copy.deepcopy(snapshot)
    current["methodology_version"] = "1.1.0"
    assert validate_published_snapshot(current) == []
    unknown = copy.deepcopy(snapshot)
    unknown["methodology_version"] = "1.2.0"
    assert any("methodology_version" in item for item in validate_published_snapshot(unknown))


def test_publish_path_does_not_import_streamlit():
    secrets = (ROOT / "runtime" / "util" / "secrets_compat.py").read_text(encoding="utf-8")
    assert not _imports_streamlit(secrets)
    weekly = (ROOT / "runtime" / "publish" / "weekly_run.py").read_text(encoding="utf-8")
    assert not _imports_streamlit(weekly)
    assert "viewer_io" not in weekly
    assert "SCHEMA_VERSION" in weekly
    for folder in PUBLISH_SCAN:
        paths = [folder] if folder.is_file() else folder.rglob("*.py")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            assert not _imports_streamlit(text), path
    assert "streamlit" not in sys.modules


def test_get_secret_reads_the_environment_only(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "from-env")
    assert get_secret("FRED_API_KEY") == "from-env"
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert get_secret("MISSING_SECRET", default=None) is None


def test_viewer_reads_the_snapshot_and_does_not_write_the_site():
    pages = [
        ROOT / "runtime" / "pages" / "dashboard.py",
        ROOT / "runtime" / "pages" / "boi_simulator.py",
        ROOT / "runtime" / "presentation" / "display_logo.py",
        ROOT / "runtime" / "main.py",
        ROOT / "runtime" / "viewer_io.py",
    ]
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "historical_bugout_index" not in text
        assert ".write_text" not in text
        assert "to_csv" not in text
        assert "weekly_run" not in text
    main = (ROOT / "runtime" / "main.py").read_text(encoding="utf-8")
    assert "st.secrets" not in main
    viewer = (ROOT / "runtime" / "viewer_io.py").read_text(encoding="utf-8")
    assert "docs" in viewer and "latest.json" in viewer
    assert not _imports_streamlit(viewer)


def test_schema_refusal_does_not_write_docs(tmp_path, monkeypatch):
    import runtime.publish.render as render
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
    monkeypatch.setattr(weekly, "fetch_markets", lambda: {"status": "success", "data": {}})
    monkeypatch.setattr(weekly, "fetch_pulse", lambda: {"status": "success", "data": {}, "dates": {}})
    monkeypatch.setattr(weekly, "fetch_revisions", lambda: {"status": "success", "payems": [], "unrate": {}})

    def _shadow():
        return {"status": "error", "message": "stub", "values": {}, "in_bugout_index": False}

    for name in (
        "fetch_labor_shadow",
        "fetch_food_shadow",
        "fetch_nyc_dhs_shadow",
        "fetch_ramsey_shelter_shadow",
        "fetch_shelter_region_shadow",
        "fetch_sf_shelter_shadow",
        "fetch_pew_trust_shadow",
        "fetch_gallup_confidence_shadow",
    ):
        monkeypatch.setattr(weekly, name, _shadow)
    monkeypatch.setattr(weekly, "validate_published_snapshot", lambda _snapshot: ["forced schema error"])

    def _should_not_render(_snapshot):
        raise AssertionError("render ran after a schema refusal")

    monkeypatch.setattr(render, "render_site", _should_not_render)
    assert weekly.main() == EXIT_SNAPSHOT_REFUSED
    assert not (tmp_path / "docs" / "latest.json").exists()
    notice = describe_publish_failure(EXIT_SNAPSHOT_REFUSED)
    assert "Refused (exit 4)" in notice
    assert "does not write" in notice or "did not write" in notice
