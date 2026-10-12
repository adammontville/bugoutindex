# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Shared footer and favicon render on every page, and the weekly render copies the icon."""
from __future__ import annotations

import json
from pathlib import Path

from runtime.publish.render import render_site

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "data" / "latest.json"
FAVICON = ROOT / "runtime" / "publish" / "static" / "favicon.ico"
FRED_LINE = (
    "This product uses the FRED® API but is not endorsed or certified "
    "by the Federal Reserve Bank of St. Louis."
)
PAGES = ("index.html", "methodology.html", "history.html", "revisions.html")


def test_render_puts_the_fred_line_and_icon_on_every_page(tmp_path, monkeypatch):
    import runtime.publish.render as render

    before = LATEST.read_bytes()
    snapshot = json.loads(before)
    monkeypatch.setattr(render, "DOCS", tmp_path)
    render_site(snapshot)

    assert LATEST.read_bytes() == before
    assert snapshot["bugout_index"] == 57.66
    assert snapshot["methodology_version"] == "1.1.0"
    icon = tmp_path / "favicon.ico"
    assert icon.read_bytes() == FAVICON.read_bytes()
    for name in PAGES:
        html = (tmp_path / name).read_text(encoding="utf-8")
        assert FRED_LINE in html
        assert '<link rel="icon" href="./favicon.ico" sizes="any">' in html


def test_committed_site_ships_the_footer_and_favicon():
    """The files GitHub Pages serves already include the line and the icon."""
    shipped = (ROOT / "docs" / "favicon.ico").read_bytes()
    assert shipped == FAVICON.read_bytes()
    for name in PAGES:
        html = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert FRED_LINE in html
        assert '<link rel="icon" href="./favicon.ico" sizes="any">' in html
