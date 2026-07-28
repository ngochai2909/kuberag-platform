ING-008 ingestion_runs counters and lifecycle

Verification:
  uv run pytest apps/ingestion/tests/unit/test_upsert.py -q --no-cov

Result: Pass on 2026-07-28 (offline InMemoryDocumentStore).

Proven fields:
- status running -> completed/failed
- fetched/inserted/updated/skipped/failed counts
- started_at / finished_at duration bounds
- sanitized error_summary (bounded, whitespace collapsed)

PostgresDocumentStore implements the same contract for later GCP runs.
