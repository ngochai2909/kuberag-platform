"""Unit tests for catalog row mapping and FakeDocumentCatalog filtering."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.providers.catalog import CategoryRecord, DocumentPage, DocumentRecord, _row_to_document


def test_row_to_document_extracts_metadata_without_content() -> None:
    document = _row_to_document(
        {
            "id": UUID("11111111-1111-1111-1111-111111111111"),
            "title": "Tiêu đề",
            "url": "https://vnexpress.net/a.html",
            "source": "vnexpress",
            "published_at": datetime(2026, 8, 1, tzinfo=UTC),
            "metadata": {
                "category": " the-thao ",
                "summary": " Tóm tắt ",
                "image_url": "https://example.com/a.jpg",
                "ignored": True,
            },
            "content": "FULL BODY MUST NOT APPEAR",
        }
    )

    assert document.category == "the-thao"
    assert document.summary == "Tóm tắt"
    assert document.image_url == "https://example.com/a.jpg"
    assert not hasattr(document, "content")


def test_row_to_document_handles_missing_metadata() -> None:
    document = _row_to_document(
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "title": "Không category",
            "url": "https://vnexpress.net/b.html",
            "source": "vnexpress",
            "published_at": None,
            "metadata": None,
        }
    )

    assert document.id == UUID("22222222-2222-2222-2222-222222222222")
    assert document.category is None
    assert document.summary is None
    assert document.image_url is None


def test_document_page_tuple_is_immutable() -> None:
    page = DocumentPage(
        documents=(
            DocumentRecord(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                title="A",
                url="https://vnexpress.net/a.html",
                source="vnexpress",
                published_at=None,
                category="x",
                summary=None,
                image_url=None,
            ),
        ),
        total=1,
        limit=24,
        offset=0,
    )
    assert page.total == 1
    assert isinstance(page.documents, tuple)
    assert CategoryRecord(category="x", count=1).count == 1
