# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Resilient HTTP GET helper used by all upstream data fetchers.

Why this exists
---------------
On 2026-04-25 the weekly Action saw FRED return HTTP 500 for several
series within the same minute, then recover. The original fetchers
issued a single `requests.get()` with no retry, so transient FRED
hiccups silently zeroed out core metrics and the index was published
with only 3 of 6 inputs.

Behavior
--------
* Retries on connection errors, timeouts, and 5xx / 408 / 429 responses.
* Exponential backoff with jitter: ~2s, 6s, 14s, 30s, 60s.
* 2xx returns immediately.
* 4xx (other than 408/429) is treated as a real error and not retried.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Optional

import requests

LOG = logging.getLogger("bugout.http_retry")

DEFAULT_RETRYABLE_STATUS = (408, 429, 500, 502, 503, 504)
DEFAULT_TIMEOUT = 25
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BACKOFF_BASE = 2.0  # seconds; attempt N waits ~base * 2**(N-1) + jitter


class RetryError(RuntimeError):
    """Raised when all retry attempts are exhausted."""


def get_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    retry_status: tuple = DEFAULT_RETRYABLE_STATUS,
    session: Optional[requests.Session] = None,
) -> requests.Response:
    """
    GET `url` with retries on transient failures.

    Returns the successful Response. Raises RetryError if every attempt
    fails. Non-retryable HTTP errors (e.g. 401, 403, 404) raise
    requests.HTTPError on the first attempt.
    """
    sess = session or requests
    last_exc: Optional[Exception] = None
    last_status: Optional[int] = None

    for attempt in range(1, max_attempts + 1):
        try:
            resp = sess.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code < 400:
                return resp
            last_status = resp.status_code
            if resp.status_code in retry_status and attempt < max_attempts:
                LOG.warning(
                    "transient HTTP %s on %s (attempt %d/%d)",
                    resp.status_code, url, attempt, max_attempts,
                )
            else:
                resp.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            LOG.warning("network error on %s: %s (attempt %d/%d)",
                        url, exc, attempt, max_attempts)
        except requests.HTTPError as exc:
            # Non-retryable 4xx: re-raise immediately.
            if last_status is not None and last_status not in retry_status:
                raise
            last_exc = exc

        if attempt < max_attempts:
            sleep_s = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
            time.sleep(sleep_s)

    raise RetryError(
        f"GET {url} failed after {max_attempts} attempts "
        f"(last_status={last_status}, last_exc={last_exc!r})"
    )
