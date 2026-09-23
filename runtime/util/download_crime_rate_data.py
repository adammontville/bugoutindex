# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Download the Real-Time Crime Index cleaned sample.

Canonical source is AH-Datalytics/rtci (public product https://realtimecrimeindex.com/).
The cleaned file the upstream README names is ``docs/app_data/final_sample.csv`` on
``main``. This module requests that object from raw.githubusercontent.com.

A GitHub blob URL is an HTML page. Writing that page over the crime file, or
treating it as a successful fetch, is a bug. Callers must use
``rtci_raw_csv_url`` and ``read_rtci_csv``, which refuse HTML and any body
that is not the RTCI sample.
"""
from __future__ import annotations

from io import StringIO
from typing import Callable, Optional, Tuple
from urllib.parse import quote

import pandas as pd

from runtime.util.http_retry import RetryError, get_with_retry

RTCI_OWNER = "AH-Datalytics"
RTCI_REPO = "rtci"
RTCI_BRANCH = "main"
RTCI_OBJECT_PATH = "docs/app_data/final_sample.csv"

# Public product. Jacob Kaplan's FBI consolidations are background only;
# they are not this download.
RTCI_PRODUCT_URL = "https://realtimecrimeindex.com/"
RTCI_REPO_URL = "https://github.com/AH-Datalytics/rtci"

# Columns the publisher's candidate rate needs. A file without them is not
# the cleaned sample, even if it happens to contain commas.
REQUIRED_COLUMNS = (
    "Date",
    "Violent Crime_mvs_12mo",
    "Property Crime_mvs_12mo",
    "FBI.Population.Covered",
)


class CrimeFileError(ValueError):
    """The RTCI body is missing, HTML, or not a usable CSV sample."""


def rtci_raw_csv_url(
    owner: str = RTCI_OWNER,
    repo: str = RTCI_REPO,
    branch: str = RTCI_BRANCH,
    path: str = RTCI_OBJECT_PATH,
) -> str:
    """Raw file URL. Never a GitHub ``blob`` HTML page."""
    quoted = "/".join(quote(part) for part in path.split("/"))
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{quoted}"


def body_is_html(text: str, content_type: Optional[str] = None) -> bool:
    """True when the payload is a web page rather than a CSV document."""
    if content_type and "html" in content_type.lower():
        return True
    sample = (text or "").lstrip("\ufeff").lstrip()[:800].lower()
    if not sample:
        return False
    if sample.startswith("<!doctype") or sample.startswith("<html") or sample.startswith("<head"):
        return True
    return "<html" in sample[:300] or "<!doctype" in sample[:300]


def read_rtci_csv(text: str, content_type: Optional[str] = None) -> pd.DataFrame:
    """Parse an RTCI sample. Raise ``CrimeFileError`` if it is not usable CSV.

    Does not compute a rate and does not decide the published index input.
    """
    if text is None or not str(text).strip():
        raise CrimeFileError("crime file is empty")
    if body_is_html(text, content_type):
        raise CrimeFileError("crime download is HTML, not a CSV")
    header = str(text).lstrip("\ufeff").splitlines()[0]
    if "," not in header or "Date" not in header:
        raise CrimeFileError("crime file does not look like a CSV")
    try:
        frame = pd.read_csv(StringIO(text))
    except Exception as exc:  # pandas ParserError and friends
        raise CrimeFileError(f"crime file is not readable CSV: {exc}") from exc
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise CrimeFileError("crime CSV missing columns: " + ", ".join(missing))
    dates = frame["Date"].dropna()
    if frame.empty or dates.empty:
        raise CrimeFileError("crime CSV has no dated rows")
    return frame


def download_rtci_csv(
    url: Optional[str] = None,
    getter: Optional[Callable[[str], Tuple[str, Optional[str]]]] = None,
) -> str:
    """Download the cleaned RTCI sample and return its text.

    ``getter`` is for tests: ``getter(url) -> (body, content_type)``.
    The default getter uses the shared HTTP retry helper. The body is
    validated before it is returned, so a blob HTML page cannot be saved
    as if it were the sample.
    """
    target = url or rtci_raw_csv_url()
    if "/blob/" in target:
        raise CrimeFileError(f"refusing GitHub blob URL (HTML page): {target}")
    try:
        if getter is None:
            response = get_with_retry(target, timeout=120)
            body = response.text
            content_type = response.headers.get("Content-Type")
        else:
            body, content_type = getter(target)
    except RetryError as exc:
        raise CrimeFileError(f"crime download failed: {exc}") from exc
    except CrimeFileError:
        raise
    except Exception as exc:
        raise CrimeFileError(f"crime download failed: {exc}") from exc
    # Parse before the caller keeps the text. HTML and broken CSV raise here.
    read_rtci_csv(body, content_type)
    return body


if __name__ == "__main__":
    print(rtci_raw_csv_url())
