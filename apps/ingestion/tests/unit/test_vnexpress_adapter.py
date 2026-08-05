from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from http_fakes import FakeHttpClient

from ingestion.adapters.vnexpress import VnExpressAdapter, extract_article_text
from ingestion.http import HttpResponse
from ingestion.models import document_checksum

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


def test_parse_feed_normalizes_items() -> None:
    adapter = VnExpressAdapter(FakeHttpClient())
    items = adapter.parse_feed(load_fixture("vnexpress", "feed.xml"))
    assert len(items) == 2
    assert items[0].title == "Robot hỗ trợ vận hành kho"
    assert items[0].link == "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html"
    assert items[1].link == "https://vnexpress.net/pin-the-ran-1002.html"
    assert items[0].enclosure_url == "https://example.invalid/robot.jpg"


def test_extract_article_text_skips_nav_and_scripts() -> None:
    text = extract_article_text(load_fixture("vnexpress", "article-1001.html"))
    assert "Menu không thuộc corpus" not in text
    assert "ignored()" not in text
    assert "Ảnh minh họa" not in text
    assert "robot tự hành" in text
    assert "30%" in text


def test_build_document_uses_article_body_and_stable_checksum() -> None:
    adapter = VnExpressAdapter(FakeHttpClient())
    item = adapter.parse_feed(load_fixture("vnexpress", "feed.xml"))[0]
    document = adapter.build_document(
        item,
        article_html=load_fixture("vnexpress", "article-1001.html"),
    )
    assert document.source == "vnexpress"
    assert document.external_id == item.link
    assert document.published_at == datetime(2026, 7, 27, 1, 15, tzinfo=UTC)
    assert document.metadata["feed_url"].endswith("khoa-hoc-cong-nghe.rss")
    assert document.metadata["category"] == "khoa-hoc-cong-nghe"
    assert document.metadata["summary"] == "Tóm tắt HTML về robot kho."
    assert document.metadata["image_url"] == "https://example.invalid/robot.jpg"
    assert document.checksum == document_checksum(title=document.title, text=document.text)
    assert "robot tự hành" in document.text


def test_fetch_documents_uses_injected_http_client() -> None:
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
        }
    )
    documents = VnExpressAdapter(http).fetch_documents()
    assert [doc.external_id for doc in documents] == [
        "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html",
        "https://vnexpress.net/pin-the-ran-1002.html",
    ]
    assert len(http.calls) == 3


def test_fetch_documents_from_feeds_skips_articles_that_fail_extraction() -> None:
    feed = load_fixture("vnexpress", "feed.xml")
    http = FakeHttpClient(
        {
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss": HttpResponse(200, feed),
            "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html": HttpResponse(
                200, "<html><body><p>no article region</p></body></html>"
            ),
            "https://vnexpress.net/pin-the-ran-1002.html": HttpResponse(
                200, load_fixture("vnexpress", "article-1002.html")
            ),
        }
    )
    documents = VnExpressAdapter(http).fetch_documents_from_feeds(
        ["https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"]
    )
    assert [doc.url for doc in documents] == ["https://vnexpress.net/pin-the-ran-1002.html"]


def test_fetch_documents_from_feeds_dedupes_shared_article_urls() -> None:
    feed = load_fixture("vnexpress", "feed.xml")
    http = FakeHttpClient(
        {
            "https://vnexpress.net/rss/tin-moi-nhat.rss": HttpResponse(200, feed),
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss": HttpResponse(200, feed),
            "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html": HttpResponse(
                200, load_fixture("vnexpress", "article-1001.html")
            ),
            "https://vnexpress.net/pin-the-ran-1002.html": HttpResponse(
                200, load_fixture("vnexpress", "article-1002.html")
            ),
        }
    )
    documents = VnExpressAdapter(http).fetch_documents_from_feeds(
        [
            "https://vnexpress.net/rss/tin-moi-nhat.rss",
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss",
        ]
    )
    assert len(documents) == 2
    assert documents[0].metadata["category"] == "tin-moi-nhat"
    # Two feed GETs + two unique article GETs; overlapping items are not refetched.
    assert len(http.calls) == 4


def test_missing_article_body_raises_without_fallback() -> None:
    adapter = VnExpressAdapter(FakeHttpClient())
    item = adapter.parse_feed(load_fixture("vnexpress", "feed.xml"))[0]
    with pytest.raises(ValueError, match="failed to extract"):
        adapter.build_document(
            item,
            article_html="<html><body><p>no article region</p></body></html>",
        )


def test_summary_fallback_when_configured() -> None:
    adapter = VnExpressAdapter(FakeHttpClient(), allow_summary_fallback=True)
    item = adapter.parse_feed(load_fixture("vnexpress", "feed.xml"))[0]
    document = adapter.build_document(
        item,
        article_html="<html><body><p>no article region</p></body></html>",
    )
    assert document.metadata["content_fallback"] == "rss_summary"
    assert document.text == "Tóm tắt HTML về robot kho."
