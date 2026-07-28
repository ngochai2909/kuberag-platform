ING-002 NVD adapter (offline fixture)

Verification:
  uv run pytest apps/ingestion/tests/unit/test_nvd_adapter.py -q

Result: Pass on 2026-07-28. Tests parse
apps/ingestion/tests/unit/fixtures/nvd/cves-sample.json into SourceDocument
records without calling services.nvd.nist.gov.

Contract sample fields: source=nvd, external_id=CVE-YYYY-NNNNN,
url=https://nvd.nist.gov/vuln/detail/{id}, English description as text,
optional metadata.cvss_*.
