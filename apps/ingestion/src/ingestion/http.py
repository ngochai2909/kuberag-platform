"""Provider-independent HTTP client with timeout, retry, and backoff."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

import httpx

DEFAULT_USER_AGENT = "KubeRAGIngestion/0.1 (+https://github.com/vin-ai/kuberag-platform; demo)"
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


class HttpError(Exception):
    """Base error for ingestion HTTP failures."""


class HttpTimeoutError(HttpError):
    """Raised when a request exceeds the configured timeout."""


class HttpStatusError(HttpError):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        detail = message or f"HTTP {status_code}"
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    text: str
    headers: Mapping[str, str] = field(default_factory=dict)


class HttpClient(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Perform an HTTP GET and return the response body as text."""


SleepFn = Callable[[float], None]
RngFn = Callable[[], float]


@dataclass(slots=True)
class RetryingHttpClient:
    """Wraps an inner HTTP client with timeout defaults and exponential backoff.

    Retries only temporary failures: connection/timeout errors, 429, and
    selected 5xx responses. Permanent 4xx responses (except 408/425/429) fail
    immediately.
    """

    inner: HttpClient
    timeout_seconds: float = 10.0
    max_attempts: int = 3
    base_delay_seconds: float = 0.05
    max_delay_seconds: float = 2.0
    user_agent: str = DEFAULT_USER_AGENT
    sleep: SleepFn = time.sleep
    random_unit: RngFn = random.random

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        request_headers = {"User-Agent": self.user_agent}
        if headers:
            request_headers.update(dict(headers))
        request_timeout = self.timeout_seconds if timeout is None else timeout

        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.inner.get(
                    url,
                    headers=request_headers,
                    timeout=request_timeout,
                )
            except HttpTimeoutError as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    raise
                self._backoff(attempt)
                continue
            except HttpError as exc:
                # httpx wraps connection refusal/reset/DNS failures as our
                # transport-level HttpError. They are transient in a scheduled
                # ingestion flow, unlike a permanent 4xx response.
                last_error = exc
                if attempt >= self.max_attempts:
                    raise
                self._backoff(attempt)
                continue

            if response.status_code < 400:
                return response

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                last_error = HttpStatusError(response.status_code)
                self._backoff(attempt)
                continue

            raise HttpStatusError(response.status_code)

        assert last_error is not None  # pragma: no cover - loop always sets error
        raise last_error

    def _backoff(self, attempt: int) -> None:
        # Full jitter: delay in [0, min(max, base * 2^(attempt-1))]
        ceiling = min(
            self.max_delay_seconds,
            self.base_delay_seconds * (2 ** (attempt - 1)),
        )
        self.sleep(ceiling * self.random_unit())


@dataclass(slots=True)
class HttpxHttpClient:
    """Live HTTP GET client backed by httpx for smoke runs and later workers."""

    timeout_seconds: float = 15.0

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        request_timeout = self.timeout_seconds if timeout is None else timeout
        try:
            with httpx.Client(follow_redirects=True, timeout=request_timeout) as client:
                response = client.get(url, headers=dict(headers or {}))
        except httpx.TimeoutException as exc:
            raise HttpTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HttpError(str(exc)) from exc
        return HttpResponse(
            status_code=response.status_code,
            text=response.text,
            headers=dict(response.headers.items()),
        )
