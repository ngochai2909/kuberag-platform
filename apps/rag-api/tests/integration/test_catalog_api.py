from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Environment, Settings
from app.main import create_app
from app.providers.catalog import (
    CatalogService,
    CategoryRecord,
    DocumentPage,
    DocumentRecord,
)
from tests.conftest import TEST_API_KEY, FakeRagService


class FakeDocumentCatalog:
    def __init__(self) -> None:
        self.categories = [
            CategoryRecord(category="the-thao", count=2),
            CategoryRecord(category="cong-nghe", count=1),
        ]
        self.documents = [
            DocumentRecord(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                title="Tin thể thao A",
                url="https://vnexpress.net/the-thao-a.html",
                source="vnexpress",
                published_at=datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
                category="the-thao",
                summary="Tóm tắt A",
                image_url="https://example.com/a.jpg",
            ),
            DocumentRecord(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                title="Tin thể thao B",
                url="https://vnexpress.net/the-thao-b.html",
                source="vnexpress",
                published_at=datetime(2026, 8, 4, 10, 0, tzinfo=UTC),
                category="the-thao",
                summary=None,
                image_url=None,
            ),
            DocumentRecord(
                id=UUID("33333333-3333-3333-3333-333333333333"),
                title="Tin công nghệ",
                url="https://vnexpress.net/cong-nghe.html",
                source="vnexpress",
                published_at=None,
                category="cong-nghe",
                summary="Tóm tắt CN",
                image_url=None,
            ),
        ]

    def list_categories(self) -> list[CategoryRecord]:
        return list(self.categories)

    def list_documents(
        self,
        *,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        items = [
            document
            for document in self.documents
            if category is None or document.category == category
        ]
        page = items[offset : offset + limit]
        return DocumentPage(
            documents=tuple(page),
            total=len(items),
            limit=limit,
            offset=offset,
        )


@pytest.fixture
def fake_catalog() -> FakeDocumentCatalog:
    return FakeDocumentCatalog()


@pytest.mark.asyncio
async def test_list_categories(
    test_settings: Settings,
    fake_rag: FakeRagService,
    fake_catalog: FakeDocumentCatalog,
) -> None:
    app = create_app(
        settings=test_settings,
        rag_service=fake_rag,
        catalog_service=CatalogService(fake_catalog),
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/categories")

    assert response.status_code == 200
    assert response.json() == {
        "categories": [
            {"category": "the-thao", "count": 2},
            {"category": "cong-nghe", "count": 1},
        ]
    }


@pytest.mark.asyncio
async def test_list_documents_filters_and_paginates(
    test_settings: Settings,
    fake_rag: FakeRagService,
    fake_catalog: FakeDocumentCatalog,
) -> None:
    app = create_app(
        settings=test_settings,
        rag_service=fake_rag,
        catalog_service=CatalogService(fake_catalog),
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/documents",
            params={"category": "the-thao", "limit": 1, "offset": 0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["documents"]) == 1
    document = body["documents"][0]
    assert document["title"] == "Tin thể thao A"
    assert document["category"] == "the-thao"
    assert document["summary"] == "Tóm tắt A"
    assert "content" not in document
    assert set(document.keys()) == {
        "id",
        "title",
        "url",
        "source",
        "published_at",
        "category",
        "summary",
        "image_url",
    }


@pytest.mark.asyncio
async def test_catalog_unavailable_without_service(unavailable_client: AsyncClient) -> None:
    categories = await unavailable_client.get("/api/v1/categories")
    documents = await unavailable_client.get("/api/v1/documents")

    assert categories.status_code == 503
    assert documents.status_code == 503


@pytest.mark.asyncio
async def test_catalog_requires_auth_when_enabled(fake_catalog: FakeDocumentCatalog) -> None:
    settings = Settings(
        _env_file=None,
        app_env=Environment.TEST,
        cors_origins="",
        api_auth_enabled=True,
        app_api_key=TEST_API_KEY,
    )
    app = create_app(
        settings=settings,
        rag_service=FakeRagService(),
        catalog_service=CatalogService(fake_catalog),
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.get("/api/v1/categories")
        valid = await client.get(
            "/api/v1/categories",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )

    assert missing.status_code == 401
    assert valid.status_code == 200


@pytest.mark.asyncio
async def test_list_documents_validation(fake_catalog: FakeDocumentCatalog) -> None:
    settings = Settings(_env_file=None, app_env=Environment.TEST, cors_origins="")
    app = create_app(
        settings=settings,
        rag_service=FakeRagService(),
        catalog_service=CatalogService(fake_catalog),
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/documents", params={"limit": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
