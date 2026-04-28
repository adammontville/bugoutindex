# Simple sanity tests for the retry helper.
import time
from unittest.mock import patch, MagicMock

import pytest
import requests

from runtime.util.http_retry import get_with_retry, RetryError


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
