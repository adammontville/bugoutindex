# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Read the published snapshot for the optional Streamlit viewer.

The weekly job does not import this module. Nothing here fetches, scores,
or writes ``docs/``.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "docs" / "data" / "latest.json"


def load_published_snapshot() -> dict | None:
    """Return ``docs/data/latest.json``, or None when it cannot be read."""
    try:
        loaded = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded
