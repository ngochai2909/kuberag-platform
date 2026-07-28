#!/usr/bin/env python3
"""Smoke-crawl a few VnExpress articles and check documents-table field mapping.

Usage:
  uv run python scripts/smoke-vnexpress-crawl.py --limit 2
  uv run python scripts/smoke-vnexpress-crawl.py --limit 2 --out tmp/vnexpress-smoke.json

This does not use Prefect, embeddings, or PostgreSQL. Output is local-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.adapters.vnexpress import DEFAULT_FEED_URL, VnExpressAdapter
from ingestion.http import HttpxHttpClient, RetryingHttpClient
from ingestion.models import SourceDocument

DOCUMENTS_COLUMNS = (
    "source",
    "external_id",
    "title",
    "url",
    "published_at",
    "content",
    "checksum",
    "metadata",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=2, help="Max articles to fetch")
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="VnExpress RSS feed URL",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional JSON output path (for example tmp/vnexpress-smoke.json)",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=180,
        help="How many content characters to print in the console summary",
    )
    return parser.parse_args()


def to_documents_row(document: SourceDocument) -> dict[str, Any]:
    """Map SourceDocument to the logical documents insert payload."""

    return {
        "source": document.source,
        "external_id": document.external_id,
        "title": document.title,
        "url": document.url,
        "published_at": document.published_at.isoformat() if document.published_at else None,
        "content": document.text,
        "checksum": document.checksum,
        "metadata": document.metadata,
    }


def validate_documents_row(row: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for column in DOCUMENTS_COLUMNS:
        if column not in row:
            problems.append(f"missing column {column}")
    if row.get("source") != "vnexpress":
        problems.append("source must be vnexpress")
    if not isinstance(row.get("external_id"), str) or not row["external_id"]:
        problems.append("external_id must be non-empty")
    if not isinstance(row.get("title"), str) or not row["title"].strip():
        problems.append("title must be non-empty")
    if not isinstance(row.get("url"), str) or not str(row["url"]).startswith("https://"):
        problems.append("url must be an https URL")
    if not isinstance(row.get("content"), str) or len(row["content"].strip()) < 40:
        problems.append("content looks too short for article body")
    if not isinstance(row.get("checksum"), str) or not _SHA256_RE.fullmatch(row["checksum"]):
        problems.append("checksum must be 64-char lowercase sha256 hex")
    if not isinstance(row.get("metadata"), dict):
        problems.append("metadata must be an object")
    published = row.get("published_at")
    if published is not None:
        try:
            datetime.fromisoformat(published)
        except ValueError:
            problems.append("published_at is not ISO-8601")
    return problems


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 2

    http = RetryingHttpClient(
        HttpxHttpClient(timeout_seconds=20.0),
        timeout_seconds=20.0,
        max_attempts=3,
        base_delay_seconds=0.5,
        max_delay_seconds=4.0,
    )
    adapter = VnExpressAdapter(http, feed_url=args.feed_url)

    print(f"Fetching feed: {args.feed_url}")
    feed_xml = http.get(args.feed_url).text
    items = adapter.parse_feed(feed_xml)
    print(f"Feed items discovered: {len(items)}")
    selected = items[: args.limit]
    if not selected:
        print("No RSS items found.", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    all_ok = True
    for index, item in enumerate(selected, start=1):
        print(f"\n[{index}/{len(selected)}] Fetching article: {item.link}")
        try:
            article_html = http.get(item.link).text
            document = adapter.build_document(item, article_html=article_html)
        except Exception as exc:
            all_ok = False
            print(f"  ERROR: {type(exc).__name__}: {exc}")
            continue

        row = to_documents_row(document)
        problems = validate_documents_row(row)
        rows.append(row)
        preview = row["content"][: args.preview_chars].replace("\n", " ")
        print(f"  title: {row['title']}")
        print(f"  url: {row['url']}")
        print(f"  external_id: {row['external_id']}")
        print(f"  published_at: {row['published_at']}")
        print(f"  checksum: {row['checksum']}")
        print(f"  content_chars: {len(row['content'])}")
        print(f"  metadata_keys: {sorted(row['metadata'].keys())}")
        print(f"  content_preview: {preview}...")
        if problems:
            all_ok = False
            print("  DB mapping: FAIL")
            for problem in problems:
                print(f"    - {problem}")
        else:
            print("  DB mapping: OK (matches documents insert fields)")

    payload = {
        "feed_url": args.feed_url,
        "fetched_count": len(rows),
        "documents_columns": list(DOCUMENTS_COLUMNS),
        "documents": rows,
    }
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote JSON: {args.out}")

    print(f"\nSummary: {len(rows)} document(s), mapping_ok={all_ok}")
    return 0 if all_ok and rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
