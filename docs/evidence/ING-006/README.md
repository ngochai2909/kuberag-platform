ING-006 Prefect pipeline end-to-end

Verification:
  uv run pytest apps/ingestion/tests/unit/test_prefect_flow.py -q --no-cov

Proven steps via `daily_ingest_flow`:
fetch → normalize → deduplicate → chunk → embed → upsert

Collaborators used in the test harness:
- FakeHttpClient + VnExpress fixtures
- FakeEmbeddingProvider (384-dim)
- InMemoryDocumentStore

Default / only source: `vnexpress`.
Second run skips unchanged documents (idempotent).

GCP cluster result: Pass on 2026-07-29 for the VnExpress path through
real e5 into CloudNativePG. Historical capture files may still mention a
brief dual-source experiment; NVD was subsequently removed from code and
the live corpus (`nvd-removed-20260729.txt`).

Runtime evidence: `gcp-flow-run.txt`.
