ING-008 ingestion_runs counters and lifecycle

Verification:
  uv run pytest apps/ingestion/tests/unit/test_upsert.py -q --no-cov

Result: Pass on 2026-07-28 (offline InMemoryDocumentStore).

Proven fields:
- status running -> completed/failed
- fetched/inserted/updated/skipped/failed counts
- started_at / finished_at duration bounds
- sanitized error_summary (bounded, whitespace collapsed)

GCP cluster result: Pass on 2026-07-29.

Three completed runs persisted in CloudNativePG with fetched/inserted/skipped/
failed counters and start/finish timestamps. Runtime evidence:
`gcp-ingestion-runs.txt`.
