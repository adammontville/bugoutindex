# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Read secrets from the process environment.

Weekly publish, a laptop, and a Raspberry Pi all set ``FRED_API_KEY`` in
the environment. This module does not import Streamlit. The value is never
written into HTML, JSON, or CSV.

    from runtime.util.secrets_compat import get_secret
    FRED_API_KEY = get_secret("FRED_API_KEY")
"""
from __future__ import annotations
import os
from typing import Optional


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return a secret from the environment, or ``default`` when it is unset."""
    env_value = os.environ.get(key)
    if env_value:
        return env_value.strip()
    return default
