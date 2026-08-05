"""Unit tests for catalog row mapping and FakeDocumentCatalog filtering."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.providers.catalog import (
    CategoryRecord,
    DocumentPage,
    DocumentRecord,
    PostgresDocumentCatalog,
    _row_to_document,
)


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


def test_postgres_catalog_lists_categories_without_selecting_content() -> None:
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"category": "khoa-hoc-cong-nghe", "count": 3},
        {"category": "the-thao", "count": 1},
    ]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    with patch("app.providers.catalog.psycopg.connect", return_value=connection) as connect:
        categories = PostgresDocumentCatalog(database_url="postgresql://fixture").list_categories()

    assert categories == [
        CategoryRecord(category="khoa-hoc-cong-nghe", count=3),
        CategoryRecord(category="the-thao", count=1),
    ]
    connect.assert_called_once_with(
        "postgresql://fixture",
        autocommit=True,
        connect_timeout=5,
    )
    statement = cursor.execute.call_args.args[0]
    assert "documents.content" not in statement
    assert "GROUP BY metadata->>'category'" in statement


def test_postgres_catalog_filters_and_pages_document_metadata() -> None:
    cursor = MagicMock()
    cursor.fetchone.return_value = {"total": 1}
    cursor.fetchall.return_value = [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "title": "Tin công nghệ",
            "url": "https://vnexpress.net/tin.html",
            "source": "vnexpress",
            "published_at": datetime(2026, 8, 5, tzinfo=UTC),
            "metadata": {"category": "khoa-hoc-cong-nghe", "summary": "Tóm tắt"},
        }
    ]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    with patch("app.providers.catalog.psycopg.connect", return_value=connection):
        page = PostgresDocumentCatalog(database_url="postgresql://fixture").list_documents(
            category="khoa-hoc-cong-nghe",
            limit=10,
            offset=20,
        )

    assert page.total == 1
    assert page.limit == 10
    assert page.offset == 20
    assert page.documents[0].summary == "Tóm tắt"
    count_statement, count_params = cursor.execute.call_args_list[0].args
    documents_statement, documents_params = cursor.execute.call_args_list[1].args
    assert "metadata->>'category' = %s" in count_statement
    assert count_params == ["khoa-hoc-cong-nghe"]
    assert "LIMIT %s OFFSET %s" in documents_statement
    assert documents_params == ["khoa-hoc-cong-nghe", 10, 20]


@pytest.mark.parametrize(
    ("database_url", "connect_timeout_seconds", "message"),
    [
        ("", 5, "database_url must not be empty"),
        ("postgresql://fixture", 0, "connect_timeout_seconds must be >= 1"),
    ],
)
def test_postgres_catalog_validates_connection_configuration(
    database_url: str,
    connect_timeout_seconds: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PostgresDocumentCatalog(
            database_url=database_url,
            connect_timeout_seconds=connect_timeout_seconds,
        )
