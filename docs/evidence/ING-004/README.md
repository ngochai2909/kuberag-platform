ING-004 HTTP timeout/retry/backoff and User-Agent

Verification:
  uv run pytest apps/ingestion/tests/unit/test_http_retry.py -q

Result: Pass on 2026-07-28. RetryingHttpClient:
- sets User-Agent KubeRAGIngestion/0.1
- applies request timeout
- retries timeouts, 429, and selected 5xx with exponential full-jitter backoff
- fails immediately on non-retryable 4xx such as 404

No live Internet calls; FakeHttpClient simulates failures offline.
