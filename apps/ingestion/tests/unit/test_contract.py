from __future__ import annotations

from pathlib import Path

from http_fakes import FakeHttpClient

from ingestion.adapters.nvd import NvdAdapter
from ingestion.adapters.vnexpress import VnExpressAdapter
from ingestion.http import HttpResponse
from ingestion.models import SourceDocument

FIXTURES = Path(__file__).parent / "fixtures"
REQUIRED_FIELDS = (
    "source",
    "external_id",
    "title",
    "url",
    "published_at",
    "text",
    "checksum",
    "metadata",
)


def load_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


def test_vnexpress_and_nvd_share_source_document_contract() -> None:
    http = FakeHttpClient(
        {
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss": HttpResponse(
                200, load_fixture("vnexpress", "feed.xml")
            ),
            "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html": HttpResponse(
                200, load_fixture("vnexpress", "article-1001.html")
            ),
            "https://vnexpress.net/pin-the-ran-1002.html": HttpResponse(
                200, load_fixture("vnexpress", "article-1002.html")
            ),
            "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=20&startIndex=0": (
                HttpResponse(200, load_fixture("nvd", "cves-sample.json"))
            ),
        }
    )

    documents = [
        *VnExpressAdapter(http).fetch_documents(),
        *NvdAdapter(http).fetch_documents(),
    ]
    assert len(documents) == 4
    for document in documents:
        assert isinstance(document, SourceDocument)
        payload = document.model_dump()
        assert set(REQUIRED_FIELDS) <= set(payload)
        assert document.source in {"vnexpress", "nvd"}
        assert len(document.checksum) == 64
        assert document.text
        assert document.url.startswith("https://")
