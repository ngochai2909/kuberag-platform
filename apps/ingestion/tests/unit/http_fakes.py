from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ingestion.http import HttpResponse, HttpTimeoutError


@dataclass
class FakeHttpClient:
    """Deterministic offline HTTP stub for adapter and retry tests."""

    responses: dict[str, HttpResponse | Exception | list[HttpResponse | Exception]] = field(
        default_factory=dict
    )
    calls: list[tuple[str, Mapping[str, str] | None, float | None]] = field(default_factory=list)

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        self.calls.append((url, headers, timeout))
        if url not in self.responses:
            raise AssertionError(f"unexpected URL requested: {url}")
        queued = self.responses[url]
        if isinstance(queued, list):
            if not queued:
                raise AssertionError(f"no remaining responses for {url}")
            item = queued.pop(0)
        else:
            item = queued
        if isinstance(item, Exception):
            raise item
        return item


def make_timeout() -> HttpTimeoutError:
    return HttpTimeoutError("simulated timeout")
