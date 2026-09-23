# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Fail-closed marker for fetchers that are not a real data source.

Calling one of these modules must not look like a successful publish.
They return no sample payload. The weekly publisher does not import them.
"""
from __future__ import annotations


class NotWiredError(RuntimeError):
    """A stub fetcher was called. It has no source and no sample data."""


def refuse(module_name: str, reason: str) -> None:
    """Raise so a caller cannot treat fiction as ``status: success``."""
    raise NotWiredError(
        f"NOT_WIRED: {module_name}. {reason} "
        "No sample payload is returned. The weekly publisher does not call this module, "
        "and it is not an input to the BugOut Index."
    )
