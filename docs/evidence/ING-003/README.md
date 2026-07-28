ING-003 Shared SourceDocument contract

Verification:
  uv run pytest apps/ingestion/tests/unit/test_contract.py -q

Result: Pass on 2026-07-28. VnExpress and NVD adapters both return
ingestion.models.SourceDocument with the required fields:
source, external_id, title, url, published_at, text, checksum, metadata.

See also docs/evidence/ING-003/contract-and-adapters.txt for the broader unit
suite output captured the same day.
