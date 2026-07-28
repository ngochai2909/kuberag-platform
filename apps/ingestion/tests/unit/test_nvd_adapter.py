from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from http_fakes import FakeHttpClient

from ingestion.adapters.nvd import NvdAdapter, select_description
from ingestion.http import HttpResponse
from ingestion.models import document_checksum

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


def test_parse_nvd_fixture_maps_stable_identity() -> None:
    adapter = NvdAdapter(FakeHttpClient())
    documents = adapter.parse_response(
        __import__("json").loads(load_fixture("nvd", "cves-sample.json"))
    )
    assert [doc.external_id for doc in documents] == ["CVE-2024-12345", "CVE-2023-99999"]
    first = documents[0]
    assert first.source == "nvd"
    assert first.url == "https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
    assert first.published_at == datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    assert first.metadata["cvss_severity"] == "CRITICAL"
    assert first.metadata["cvss_version"] == "3.1"
    assert first.checksum == document_checksum(title=first.title, text=first.text)
    assert "buffer overflow" in first.text


def test_select_description_prefers_english() -> None:
    text = select_description(
        [
            {"lang": "es", "value": "espanol"},
            {"lang": "en", "value": "english body"},
        ]
    )
    assert text == "english body"


def test_fetch_documents_builds_query_and_parses() -> None:
    payload = load_fixture("nvd", "cves-sample.json")
    url = (
        "https://services.nvd.nist.gov/rest/json/cves/2.0"
        "?resultsPerPage=20&startIndex=0"
        "&pubStartDate=2024-01-01T00%3A00%3A00.000%2B00%3A00"
        "&pubEndDate=2024-01-31T23%3A59%3A59.000%2B00%3A00"
    )
    http = FakeHttpClient({url: HttpResponse(200, payload)})
    documents = NvdAdapter(http).fetch_documents(
        pub_start=datetime(2024, 1, 1, tzinfo=UTC),
        pub_end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
    )
    assert len(documents) == 2
    assert http.calls[0][0] == url
