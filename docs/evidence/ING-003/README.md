ING-003 SourceDocument contract

Verification:
  uv run pytest apps/ingestion/tests/unit/test_contract.py -q

Result: Pass. VnExpress adapter returns ingestion.models.SourceDocument with
the required fields: source, external_id, title, url, published_at, text,
checksum, metadata.

See also docs/evidence/ING-003/contract-and-adapters.txt for a broader unit
suite capture from 2026-07-28 (historical output may still mention the
removed NVD adapter path).
