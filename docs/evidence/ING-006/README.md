ING-006 Prefect pipeline end-to-end (offline fakes)

Verification:
  uv run pytest apps/ingestion/tests/unit/test_prefect_flow.py -q --no-cov

Result: Pass on 2026-07-28 for the offline path.

Proven steps via `daily_ingest_flow`:
fetch → normalize → deduplicate → chunk → embed → upsert

Collaborators used in the test harness:
- FakeHttpClient + VnExpress/NVD fixtures
- FakeEmbeddingProvider (384-dim)
- InMemoryDocumentStore

Second run skips unchanged documents (idempotent).

Pending for cluster evidence:
- Flow run against live Prefect worker + PostgreSQL + real e5
