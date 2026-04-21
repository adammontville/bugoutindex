# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Secrets compatibility shim.

The original fetchers used `st.secrets[...]` which only works inside a
Streamlit runtime. For headless execution (GitHub Actions, cron, CLI), we
fall back to `os.environ`. Usage:

    from runtime.util.secrets_compat import get_secret
    FRED_API_KEY = get_secret("FRED_API_KEY")
"""
from __future__ import annotations
import os
from typing import Optional


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return a secret from Streamlit secrets if available, else from env vars."""
    # Prefer env vars when running headless (CI, cron, CLI).
    env_value = os.environ.get(key)
    if env_value:
        return env_value.strip()

    # Fall back to Streamlit secrets if available and configured.
    try:
        import streamlit as st  # type: ignore
        try:
            value = st.secrets[key]  # type: ignore[attr-defined]
            if value:
                return str(value).strip()
        except Exception:
            pass
    except ImportError:
        pass

    return default
