from __future__ import annotations

import pytest
from http_fakes import FakeHttpClient, make_timeout

from ingestion.http import (
    DEFAULT_USER_AGENT,
    HttpResponse,
    HttpStatusError,
    HttpTimeoutError,
    RetryingHttpClient,
)


def test_retrying_client_sets_user_agent_and_timeout() -> None:
    inner = FakeHttpClient({"https://example.invalid/ok": HttpResponse(200, "ok")})
    client = RetryingHttpClient(inner, timeout_seconds=7.5, sleep=lambda _: None)
    response = client.get("https://example.invalid/ok")
    assert response.text == "ok"
    url, headers, timeout = inner.calls[0]
    assert url == "https://example.invalid/ok"
    assert headers is not None
    assert headers["User-Agent"] == DEFAULT_USER_AGENT
    assert timeout == 7.5


def test_retries_timeout_then_succeeds() -> None:
    sleeps: list[float] = []
    inner = FakeHttpClient(
        {
            "https://example.invalid/flaky": [
                make_timeout(),
                HttpResponse(200, "recovered"),
            ]
        }
    )
    client = RetryingHttpClient(
        inner,
        max_attempts=3,
        base_delay_seconds=0.1,
        sleep=sleeps.append,
        random_unit=lambda: 1.0,
    )
    assert client.get("https://example.invalid/flaky").text == "recovered"
    assert len(inner.calls) == 2
    assert sleeps == [0.1]


def test_retries_429_and_503_then_succeeds() -> None:
    sleeps: list[float] = []
    inner = FakeHttpClient(
        {
            "https://example.invalid/limited": [
                HttpResponse(429, "slow down"),
                HttpResponse(503, "unavailable"),
                HttpResponse(200, "ok"),
            ]
        }
    )
    client = RetryingHttpClient(
        inner,
        max_attempts=3,
        base_delay_seconds=0.05,
        sleep=sleeps.append,
        random_unit=lambda: 1.0,
    )
    assert client.get("https://example.invalid/limited").text == "ok"
    assert len(inner.calls) == 3
    assert sleeps == [0.05, 0.1]


def test_non_retryable_4xx_fails_immediately() -> None:
    inner = FakeHttpClient({"https://example.invalid/missing": HttpResponse(404, "gone")})
    client = RetryingHttpClient(inner, sleep=lambda _: None)
    with pytest.raises(HttpStatusError) as exc_info:
        client.get("https://example.invalid/missing")
    assert exc_info.value.status_code == 404
    assert len(inner.calls) == 1


def test_exhausts_retries_on_persistent_timeout() -> None:
    inner = FakeHttpClient(
        {
            "https://example.invalid/down": [
                HttpTimeoutError("t1"),
                HttpTimeoutError("t2"),
                HttpTimeoutError("t3"),
            ]
        }
    )
    client = RetryingHttpClient(inner, max_attempts=3, sleep=lambda _: None)
    with pytest.raises(HttpTimeoutError):
        client.get("https://example.invalid/down")
    assert len(inner.calls) == 3
