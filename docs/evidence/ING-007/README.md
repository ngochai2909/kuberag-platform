ING-007 Idempotent upsert (no duplicate growth)

Verification:
  uv run pytest apps/ingestion/tests/unit/test_upsert.py -q --no-cov

Result: Pass on 2026-07-28 (offline InMemoryDocumentStore).

Rules proven:
- First run inserts documents + chunks
- Second identical run skips by checksum; document/chunk counts unchanged
- Changed checksum updates the same document id and replaces chunks
