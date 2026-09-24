# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Strip credentials from text before it is logged or published.

FRED calls pass the API key as a query parameter. ``requests`` then copies
the full URL, key included, into ``HTTPError`` and connection-error text.
Those strings are not safe to store.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable
from urllib.parse import quote, quote_plus

_REDACTED = "[REDACTED]"
_MIN_LITERAL = 8

# Credential names. ``key`` is only treated as a secret when it is a query
# parameter (``?key=`` / ``&key=``). A bare ``key=`` shows up in ordinary
# tracebacks such as ``sort(key=lambda ...)``.
_NAMED_PARAM = (
    r"api[_-]?key|apikey|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|auth_token|password|passwd"
)
_QUERY_PARAM = _NAMED_PARAM + r"|authorization|secret|token|key|auth"
_VALUE = r"[^&#\s\"'),}]+"

_QUERY_RE = re.compile(rf"(?i)([?&](?:{_QUERY_PARAM})=){_VALUE}")
_ASSIGN_RE = re.compile(rf"(?i)\b((?:{_NAMED_PARAM})\s*=\s*){_VALUE}")
_HEADER_RE = re.compile(
    r"(?i)\b((?:authorization|proxy-authorization|x-api-key|api-key|api_key|"
    rf"x-auth-token|x-access-token)\s*[:=]\s*)(?:bearer\s+)?{_VALUE}"
)

_SENSITIVE_NAMES = {
    "api-key",
    "apikey",
    "api_key",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
    "client-secret",
    "client_secret",
    "auth",
    "auth-token",
    "auth_token",
    "authorization",
    "password",
    "passwd",
    "secret",
    "token",
    "key",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "proxy-authorization",
}

_ENV_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_PASSWD")


def _named_secret(name: object) -> bool:
    text = str(name).strip().lower()
    hyphenated = text.replace("_", "-")
    return text in _SENSITIVE_NAMES or hyphenated in _SENSITIVE_NAMES


def secret_values(*mappings: object) -> list[str]:
    """Credential values from request params and headers."""
    found: list[str] = []
    for mapping in mappings:
        if not mapping:
            continue
        items = mapping.items() if hasattr(mapping, "items") else ()
        for name, value in items:
            if not _named_secret(name) or value is None:
                continue
            text = str(value).strip()
            if text:
                found.append(text)
    return found


def _env_secrets() -> list[str]:
    found: list[str] = []
    for name, value in os.environ.items():
        upper = name.upper()
        if upper != "FRED_API_KEY" and not any(upper.endswith(suffix) for suffix in _ENV_SUFFIXES):
            continue
        text = (value or "").strip()
        if len(text) >= _MIN_LITERAL:
            found.append(text)
    return found


def _literal_variants(secret: str) -> list[str]:
    variants = [secret]
    if secret.lower().startswith("bearer "):
        token = secret.split(None, 1)[1].strip()
        if len(token) >= _MIN_LITERAL:
            variants.append(token)
    encoded = []
    for value in list(variants):
        for form in (quote(value, safe=""), quote_plus(value)):
            if form and form not in variants and form not in encoded:
                encoded.append(form)
        dumped = json.dumps(value)[1:-1]
        if dumped and dumped != value and dumped not in variants and dumped not in encoded:
            encoded.append(dumped)
    return variants + encoded


def redact_secrets(text: str, secrets: Iterable[str] | None = None) -> str:
    """Remove credential values from exception text, URLs, and headers.

    Recognized query parameters and auth headers are always masked. Known
    secret values (request params, headers, and credential env vars of at
    least eight characters) are masked wherever they appear.
    """
    if not text:
        return text
    values: list[str] = []
    for secret in list(secrets or ()) + _env_secrets():
        if secret is None:
            continue
        text_secret = str(secret).strip()
        if len(text_secret) >= _MIN_LITERAL:
            values.extend(_literal_variants(text_secret))
    redacted = text
    for secret in sorted(set(values), key=len, reverse=True):
        redacted = redacted.replace(secret, _REDACTED)
    redacted = _QUERY_RE.sub(rf"\1{_REDACTED}", redacted)
    redacted = _ASSIGN_RE.sub(rf"\1{_REDACTED}", redacted)
    redacted = _HEADER_RE.sub(rf"\1{_REDACTED}", redacted)
    return redacted


def scrub_published(value: Any) -> Any:
    """Walk a snapshot and redact every string before it is written out."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {key: scrub_published(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_published(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_published(item) for item in value)
    return value
