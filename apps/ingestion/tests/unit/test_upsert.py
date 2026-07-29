from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ingestion.chunking import ChunkingConfig, TextChunk
from ingestion.models import SourceDocument, document_checksum
from ingestion.store import InMemoryDocumentStore
from ingestion.upsert import (
    DocumentUpserter,
    run_idempotent_upsert,
    sanitize_error_summary,
    start_ingestion_run,
)


def _document(
    *,
    external_id: str = "https://vnexpress.net/demo-1.html",
    title: str = "Demo article",
    text: str = "Câu một về robot kho. Câu hai về cảm biến.",
    source: str = "vnexpress",
) -> SourceDocument:
    return SourceDocument(
        source=source,
        external_id=external_id,
        title=title,
        url=external_id
        if external_id.startswith("http")
        else f"https://example.invalid/{external_id}",
        published_at=datetime(2026, 7, 28, tzinfo=UTC),
        text=text,
        checksum=document_checksum(title=title, text=text),
        metadata={"feed_url": "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"},
    )


def test_first_upsert_inserts_document_and_chunks() -> None:
    store = InMemoryDocumentStore()
    upserter = DocumentUpserter(
        store,
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    result = upserter.upsert(_document())
    assert result.action == "inserted"
    assert result.chunk_count >= 1
    assert store.count_documents() == 1
    assert store.count_chunks() == result.chunk_count


def test_second_identical_upsert_is_skipped_without_duplicates() -> None:
    store = InMemoryDocumentStore()
    docs = [
        _document(),
        _document(external_id="https://vnexpress.net/demo-2.html", text="Bài hai."),
    ]
    first, first_results = run_idempotent_upsert(
        store,
        docs,
        flow_name="ingest-vnexpress",
        source_scope="vnexpress:khoa-hoc-cong-nghe",
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    assert first.status == "completed"
    assert first.counters.inserted_count == 2
    assert first.counters.skipped_count == 0
    documents_after_first = store.count_documents()
    chunks_after_first = store.count_chunks()

    second, second_results = run_idempotent_upsert(
        store,
        docs,
        flow_name="ingest-vnexpress",
        source_scope="vnexpress:khoa-hoc-cong-nghe",
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    assert [item.action for item in second_results] == ["skipped", "skipped"]
    assert second.counters.inserted_count == 0
    assert second.counters.updated_count == 0
    assert second.counters.skipped_count == 2
    assert store.count_documents() == documents_after_first
    assert store.count_chunks() == chunks_after_first
    assert first_results[0].document_id == second_results[0].document_id


def test_changed_checksum_replaces_chunks() -> None:
    store = InMemoryDocumentStore()
    upserter = DocumentUpserter(
        store,
        chunking=ChunkingConfig(max_chars=120, overlap_chars=20),
    )
    original = _document(text="Phiên bản một ngắn.")
    first = upserter.upsert(original)
    assert first.action == "inserted"
    original_chunks = store.list_chunks(first.document_id)
    assert original_chunks

    updated = _document(
        text=(
            "Phiên bản hai dài hơn nhiều để tạo chunk mới. "
            "Thêm câu nữa về cập nhật nội dung bài viết."
        )
    )
    second = upserter.upsert(updated)
    assert second.action == "updated"
    assert second.document_id == first.document_id
    assert store.count_documents() == 1
    new_chunks = store.list_chunks(second.document_id)
    assert new_chunks
    assert [chunk.content for chunk in new_chunks] != [chunk.content for chunk in original_chunks]
    assert store.get_document(updated.source, updated.external_id) is not None
    assert store.get_document(updated.source, updated.external_id).checksum == updated.checksum  # type: ignore[union-attr]


def test_ingestion_run_records_success_counts_and_duration() -> None:
    store = InMemoryDocumentStore()
    session = start_ingestion_run(
        store,
        flow_name="ingest-vnexpress",
        source_scope="vnexpress:khoa-hoc-cong-nghe",
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    session.upsert_document(
        _document(
            source="vnexpress",
            external_id="https://vnexpress.net/demo-article.html",
            title="Tin công nghệ demo",
            text="A demo technology article description for upsert tests.",
        )
    )
    finished = session.complete()
    assert finished.status == "completed"
    assert finished.counters.fetched_count == 1
    assert finished.counters.inserted_count == 1
    assert finished.started_at is not None
    assert finished.finished_at is not None
    assert finished.finished_at >= finished.started_at
    loaded = store.get_ingestion_run(finished.id)
    assert loaded is not None
    assert loaded.counters.inserted_count == 1


def test_ingestion_run_failure_keeps_sanitized_error_summary() -> None:
    store = InMemoryDocumentStore()
    session = start_ingestion_run(
        store,
        flow_name="ingest-vnexpress",
        source_scope="vnexpress:khoa-hoc-cong-nghe",
    )
    session.record_failure(ValueError("boom " + ("x" * 600)))
    finished = session.complete()
    assert finished.status == "failed"
    assert finished.counters.failed_count == 1
    assert finished.error_summary is not None
    assert len(finished.error_summary) <= 500
    assert "boom" in finished.error_summary


def test_sanitize_error_summary_collapses_whitespace() -> None:
    summary = sanitize_error_summary("line1\n\nline2")
    assert summary == "line1 line2"


def test_explicit_chunks_bypass_chunker() -> None:
    store = InMemoryDocumentStore()
    upserter = DocumentUpserter(store)
    chunks = [
        TextChunk(chunk_index=0, content="only-chunk", metadata={"max_chars": 100}),
    ]
    result = upserter.upsert(_document(), chunks=chunks)
    assert result.action == "inserted"
    assert result.chunk_count == 1
    assert store.list_chunks(result.document_id)[0].content == "only-chunk"


def test_upsert_many_and_session_fail() -> None:
    store = InMemoryDocumentStore()
    upserter = DocumentUpserter(
        store,
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    results = upserter.upsert_many(
        [
            _document(),
            _document(external_id="https://vnexpress.net/demo-3.html", text="Bài ba."),
        ]
    )
    assert [item.action for item in results] == ["inserted", "inserted"]

    session = start_ingestion_run(
        store,
        flow_name="ingest-vnexpress",
        source_scope="vnexpress:khoa-hoc-cong-nghe",
    )
    finished = session.fail("operator aborted run")
    assert finished.status == "failed"
    assert finished.error_summary == "operator aborted run"


def test_inmemory_store_rejects_invalid_mutations() -> None:
    store = InMemoryDocumentStore()
    doc = _document()
    upserter = DocumentUpserter(store, chunking=ChunkingConfig(max_chars=200, overlap_chars=40))
    inserted = upserter.upsert(doc)
    with pytest.raises(ValueError, match="already exists"):
        store.insert_document(doc, [])
    with pytest.raises(ValueError, match="not found for update"):
        store.update_document(inserted.document_id, _document(external_id="missing"), [])

    run = store.start_ingestion_run(flow_name="x", source_scope="y")
    with pytest.raises(ValueError, match="completed or failed"):
        store.finish_ingestion_run(
            run.id,
            status="running",
            counters=store.get_ingestion_run(run.id).counters,  # type: ignore[union-attr]
        )
