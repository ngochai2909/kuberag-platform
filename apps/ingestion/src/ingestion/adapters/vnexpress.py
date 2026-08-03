"""VnExpress RSS discovery + article body extraction adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

from ingestion.http import HttpClient
from ingestion.models import SourceDocument, document_checksum, normalize_whitespace

DEFAULT_FEED_URL = "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"
EXTRACTION_VERSION = "vnexpress-article-v2"

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)\b[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class RssItem:
    title: str
    link: str
    guid: str | None
    pub_date: str | None
    description_html: str | None
    enclosure_url: str | None


class _ArticleTextExtractor(HTMLParser):
    """Collect visible text from the main article content region.

    VnExpress pages nest the article body after navigation markup and may have
    imperfect tag pairing. Capture starts when ``article``/``fck_detail`` opens,
    and chrome tags are skipped only while that region is active.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_depth = 0
        self._skip_depth = 0
        self._chunks: list[str] = []

    @property
    def text(self) -> str:
        return normalize_whitespace(" ".join(self._chunks))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: (value or "") for key, value in attrs}
        classes = set(attr_map.get("class", "").split())

        if tag == "article" or "fck_detail" in classes:
            self._capture_depth = 1
            self._skip_depth = 0
            return

        if not self._capture_depth:
            # Fixture-only fallback: bare Normal paragraphs without article wrap.
            if tag == "p" and "Normal" in classes:
                self._capture_depth = 1
            return

        if self._skip_depth:
            self._skip_depth += 1
            return
        if tag in {"script", "style", "noscript", "figure", "figcaption", "nav", "aside"}:
            self._skip_depth = 1
            return
        self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if self._capture_depth:
            self._capture_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_depth and not self._skip_depth:
            stripped = data.strip()
            if stripped:
                self._chunks.append(stripped)


class VnExpressAdapter:
    """Normalize VnExpress RSS items and article HTML into SourceDocument."""

    source = "vnexpress"

    def __init__(
        self,
        http: HttpClient,
        *,
        feed_url: str = DEFAULT_FEED_URL,
        allow_summary_fallback: bool = False,
    ) -> None:
        self._http = http
        self._feed_url = feed_url
        self._allow_summary_fallback = allow_summary_fallback

    def fetch_documents(self) -> list[SourceDocument]:
        response = self._http.get(self._feed_url)
        items = self.parse_feed(response.text)
        documents: list[SourceDocument] = []
        for item in items:
            article = self._http.get(item.link)
            documents.append(self.build_document(item, article_html=article.text))
        return documents

    def parse_feed(self, xml_text: str) -> list[RssItem]:
        root = ElementTree.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            msg = "RSS feed is missing channel"
            raise ValueError(msg)

        items: list[RssItem] = []
        for item in channel.findall("item"):
            title = normalize_whitespace(self._child_text(item, "title") or "")
            link = normalize_canonical_url(self._child_text(item, "link") or "")
            if not title or not link:
                continue
            guid = self._child_text(item, "guid")
            enclosure = item.find("enclosure")
            enclosure_url = enclosure.get("url") if enclosure is not None else None
            items.append(
                RssItem(
                    title=title,
                    link=link,
                    guid=normalize_canonical_url(guid) if guid else None,
                    pub_date=self._child_text(item, "pubDate"),
                    description_html=self._child_text(item, "description"),
                    enclosure_url=enclosure_url,
                )
            )
        return items

    def build_document(self, item: RssItem, *, article_html: str) -> SourceDocument:
        text = extract_article_text(article_html)
        metadata: dict[str, Any] = {
            "feed_url": self._feed_url,
            "extraction_version": EXTRACTION_VERSION,
            "summary": strip_html(item.description_html or ""),
        }
        if item.enclosure_url:
            metadata["image_url"] = item.enclosure_url

        if not text:
            if not self._allow_summary_fallback:
                msg = f"failed to extract article text for {item.link}"
                raise ValueError(msg)
            text = metadata["summary"]
            metadata["content_fallback"] = "rss_summary"
            if not text:
                msg = f"no extractable content for {item.link}"
                raise ValueError(msg)

        external_id = item.guid or item.link
        return SourceDocument(
            source=self.source,
            external_id=external_id,
            title=item.title,
            url=item.link,
            published_at=parse_rss_datetime(item.pub_date),
            text=text,
            checksum=document_checksum(title=item.title, text=text),
            metadata=metadata,
        )

    @staticmethod
    def _child_text(parent: ElementTree.Element, tag: str) -> str | None:
        child = parent.find(tag)
        if child is None or child.text is None:
            return None
        return child.text


def normalize_canonical_url(url: str) -> str:
    cleaned = normalize_whitespace(url)
    parts = urlsplit(cleaned)
    # Drop fragment; keep query only when present (VnExpress article IDs are path-based).
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def parse_rss_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def strip_html(value: str) -> str:
    without_blocks = _SCRIPT_STYLE_RE.sub(" ", value)
    return normalize_whitespace(_TAG_RE.sub(" ", without_blocks))


def extract_article_text(html: str) -> str:
    parser = _ArticleTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text
