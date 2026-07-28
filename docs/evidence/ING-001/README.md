ING-001 VnExpress adapter (offline fixture)

Verification:
  uv run pytest apps/ingestion/tests/unit/test_vnexpress_adapter.py -q

Result: Pass on 2026-07-28. Tests parse the local RSS/HTML fixtures under
apps/ingestion/tests/unit/fixtures/vnexpress/ and build SourceDocument records
without Internet access.

Contract sample fields: source=vnexpress, external_id=canonical article URL,
title/url/published_at/text/checksum/metadata.feed_url.
