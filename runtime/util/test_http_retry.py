# Simple sanity tests for the retry helper.
import logging
import traceback
from unittest.mock import patch

import pytest
import requests

from runtime.util.http_retry import get_with_retry, RetryError

FAKE_KEY = "fk_test_fred_0123456789abcdef"
FAKE_HEADER = "hdr_test_bearer_0123456789abcdef"


class FakeResp:
    def __init__(self, status):
        self.status_code = status
        self.text = ""

    def json(self):
        return {"ok": True}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} mock")


def test_returns_on_first_success():
    with patch("requests.get", return_value=FakeResp(200)) as g:
        resp = get_with_retry("http://x", max_attempts=3, backoff_base=0)
        assert resp.status_code == 200
        assert g.call_count == 1


def test_retries_on_500_then_succeeds():
    seq = [FakeResp(500), FakeResp(500), FakeResp(200)]
    with patch("requests.get", side_effect=seq) as g:
        resp = get_with_retry("http://x", max_attempts=5, backoff_base=0)
        assert resp.status_code == 200
        assert g.call_count == 3


def test_gives_up_after_max_attempts():
    with patch("requests.get", return_value=FakeResp(503)):
        with pytest.raises(RetryError):
            get_with_retry("http://x", max_attempts=3, backoff_base=0)


def test_4xx_does_not_retry():
    with patch("requests.get", return_value=FakeResp(404)) as g:
        with pytest.raises(requests.HTTPError):
            get_with_retry("http://x", max_attempts=5, backoff_base=0)
        assert g.call_count == 1


def test_429_does_retry():
    seq = [FakeResp(429), FakeResp(200)]
    with patch("requests.get", side_effect=seq) as g:
        resp = get_with_retry("http://x", max_attempts=3, backoff_base=0)
        assert resp.status_code == 200
        assert g.call_count == 2


def _url_with_key(key: str = FAKE_KEY) -> str:
    return (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=PAYEMS&api_key={key}&file_type=json"
    )


class _LeakyResp:
    """Mimic requests.Response.raise_for_status, which embeds response.url."""

    def __init__(self, status: int, url: str, body: str):
        self.status_code = status
        self.url = url
        self.text = body
        self.reason = "Internal Server Error" if status >= 500 else "Forbidden"

    def raise_for_status(self):
        if self.status_code >= 400:
            kind = "Server" if self.status_code >= 500 else "Client"
            raise requests.HTTPError(
                f"{self.status_code} {kind} Error: {self.reason} for url: {self.url}"
            )


def test_retry_error_drops_key_from_url_header_and_exception(caplog):
    caplog.set_level(logging.WARNING, logger="bugout.http_retry")

    def fake_get(url, params=None, headers=None, timeout=None):
        key = (params or {}).get("api_key", "")
        token = (headers or {}).get("Authorization", "")
        raise requests.ConnectionError(
            "HTTPSConnectionPool(host='api.stlouisfed.org', port=443): "
            f"Max retries exceeded with url: {_url_with_key(key)} "
            f"(Caused by Authorization: {token}; rejected {key})"
        )

    with patch("requests.get", side_effect=fake_get):
        with pytest.raises(RetryError) as caught:
            get_with_retry(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": "PAYEMS", "api_key": FAKE_KEY, "file_type": "json"},
                headers={"Authorization": f"Bearer {FAKE_HEADER}"},
                max_attempts=2,
                backoff_base=0,
            )

    message = str(caught.value)
    rendered = "".join(traceback.format_exception(caught.value))
    assert FAKE_KEY not in message
    assert FAKE_HEADER not in message
    assert FAKE_KEY not in rendered
    assert FAKE_HEADER not in rendered
    assert FAKE_KEY not in caplog.text
    assert FAKE_HEADER not in caplog.text
    assert "PAYEMS" in message
    assert "failed after 2 attempts" in message
    assert caught.value.__cause__ is None


def test_nonretryable_http_error_drops_the_key_from_the_url():
    url = _url_with_key()
    with patch("requests.get", return_value=_LeakyResp(403, url, f"bad {FAKE_KEY}")):
        with pytest.raises(requests.HTTPError) as caught:
            get_with_retry(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"api_key": FAKE_KEY},
                headers={"X-Api-Key": FAKE_HEADER},
                max_attempts=4,
                backoff_base=0,
            )

    message = str(caught.value)
    rendered = "".join(traceback.format_exception(caught.value))
    assert FAKE_KEY not in message
    assert FAKE_HEADER not in message
    assert FAKE_KEY not in rendered
    assert "403" in message
    assert "series_id=PAYEMS" in message or "PAYEMS" in message
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
