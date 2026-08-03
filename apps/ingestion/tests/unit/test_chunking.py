from __future__ import annotations

from datetime import UTC, datetime
from itertools import pairwise

import pytest

from ingestion.chunking import ChunkingConfig, chunk_document, chunk_text
from ingestion.models import SourceDocument, document_checksum


def _doc(text: str, title: str = "Tiêu đề bài viết") -> SourceDocument:
    return SourceDocument(
        source="vnexpress",
        external_id="https://vnexpress.net/example-1000.html",
        title=title,
        url="https://vnexpress.net/example-1000.html",
        published_at=datetime(2026, 7, 28, tzinfo=UTC),
        text=text,
        checksum=document_checksum(title=title, text=text),
        metadata={"feed_url": "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"},
    )


def test_short_document_is_single_title_prefixed_chunk() -> None:
    text = "Nhà kho dùng robot tự hành để sắp xếp hàng. Hệ thống giảm thời gian lấy hàng."
    chunks = chunk_document(_doc(text), config=ChunkingConfig(max_chars=400, overlap_chars=50))
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content.startswith("Tiêu đề bài viết\n\n")
    assert "robot tự hành" in chunks[0].content
    assert chunks[0].metadata["title_prefixed"] is True
    assert len(chunks[0].content) <= 400


def test_sentence_boundaries_are_preferred_over_mid_sentence_cuts() -> None:
    sentences = [
        "Câu mở đầu giới thiệu robot kho hàng thông minh.",
        "Câu hai mô tả cảm biến lidar và camera độ sâu.",
        "Câu ba nêu kết quả giảm 30 phần trăm thời gian lấy hàng.",
        "Câu bốn nói về kế hoạch mở rộng sang nhiều kho khác.",
        "Câu năm kết luận hệ thống đã ổn định sau ba tháng.",
    ]
    text = " ".join(sentences)
    chunks = chunk_text(
        text,
        title="Robot kho",
        config=ChunkingConfig(max_chars=180, overlap_chars=40, include_title=True),
    )
    assert len(chunks) >= 2
    bodies = [chunk.content.split("\n\n", maxsplit=1)[1] for chunk in chunks]
    # Each emitted body should end on a sentence boundary when possible.
    for body in bodies[:-1]:
        assert body.endswith(".")
    # No chunk should start mid-word from the previous sentence without the
    # overlapping sentence being whole.
    for body in bodies:
        assert not body.startswith("phần trăm")


def test_overlap_keeps_context_between_adjacent_chunks() -> None:
    sentences = [f"Đây là câu số {index} trong bài viết kỹ thuật dài." for index in range(1, 13)]
    text = " ".join(sentences)
    chunks = chunk_text(
        text,
        title="Overlap",
        config=ChunkingConfig(max_chars=160, overlap_chars=50, include_title=True),
    )
    assert len(chunks) >= 3
    for left, right in pairwise(chunks):
        left_body = left.content.split("\n\n", maxsplit=1)[1]
        right_body = right.content.split("\n\n", maxsplit=1)[1]
        # Shared sentence fragment proves overlap context for retrieval.
        assert any(sentence in right_body for sentence in left_body.split(". ") if sentence.strip())


def test_oversized_sentence_is_hard_split_without_exceeding_budget() -> None:
    long_sentence = "Từ " + ("dài " * 80) + "kết thúc."
    chunks = chunk_text(
        long_sentence,
        title="Hard",
        config=ChunkingConfig(max_chars=120, overlap_chars=20),
    )
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.content) <= 120


def test_zero_overlap_does_not_repeat_sentences() -> None:
    text = (
        "Câu một ngắn gọn. Câu hai ngắn gọn. Câu ba ngắn gọn. Câu bốn ngắn gọn. "
        "Câu năm ngắn gọn. Câu sáu ngắn gọn. Câu bảy ngắn gọn. Câu tám ngắn gọn."
    )
    chunks = chunk_text(
        text,
        title=None,
        config=ChunkingConfig(max_chars=64, overlap_chars=0, include_title=False),
    )
    joined = " ".join(chunk.content for chunk in chunks)
    assert joined.count("Câu một ngắn gọn.") == 1
    assert joined.count("Câu tám ngắn gọn.") == 1


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError, match="overlap_chars must be smaller"):
        ChunkingConfig(max_chars=100, overlap_chars=100)


def test_chunk_indexes_are_contiguous() -> None:
    text = " ".join(f"Mệnh đề số {i} hoàn chỉnh." for i in range(20))
    chunks = chunk_document(
        _doc(text),
        config=ChunkingConfig(max_chars=200, overlap_chars=40),
    )
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata["chunking_version"] == "sentence-overlap-v1" for chunk in chunks)
