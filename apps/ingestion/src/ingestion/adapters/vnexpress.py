"""VnExpress RSS discovery + article body extraction adapter."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

from ingestion.http import HttpClient
from ingestion.models import SourceDocument, document_checksum, normalize_whitespace

logger = logging.getLogger(__name__)

EXTRACTION_VERSION = "vnexpress-article-v2"


@dataclass(frozen=True, slots=True)
class VnExpressFeed:
    """One public VnExpress RSS channel used for discovery."""

    category: str
    url: str


# Working public channels from https://vnexpress.net/rss (probed 200 + items>0).
# Overlapping headlines across feeds are deduplicated by canonical URL before
# article download so multi-feed ingest does not refetch the same page.
DEFAULT_FEEDS: tuple[VnExpressFeed, ...] = (
    VnExpressFeed("tin-moi-nhat", "https://vnexpress.net/rss/tin-moi-nhat.rss"),
    VnExpressFeed("tin-noi-bat", "https://vnexpress.net/rss/tin-noi-bat.rss"),
    VnExpressFeed("thoi-su", "https://vnexpress.net/rss/thoi-su.rss"),
    VnExpressFeed("the-gioi", "https://vnexpress.net/rss/the-gioi.rss"),
    VnExpressFeed("kinh-doanh", "https://vnexpress.net/rss/kinh-doanh.rss"),
    VnExpressFeed("bat-dong-san", "https://vnexpress.net/rss/bat-dong-san.rss"),
    VnExpressFeed("khoa-hoc-cong-nghe", "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"),
    VnExpressFeed("giai-tri", "https://vnexpress.net/rss/giai-tri.rss"),
    VnExpressFeed("the-thao", "https://vnexpress.net/rss/the-thao.rss"),
    VnExpressFeed("phap-luat", "https://vnexpress.net/rss/phap-luat.rss"),
    VnExpressFeed("giao-duc", "https://vnexpress.net/rss/giao-duc.rss"),
    VnExpressFeed("suc-khoe", "https://vnexpress.net/rss/suc-khoe.rss"),
    VnExpressFeed("doi-song", "https://vnexpress.net/rss/doi-song.rss"),
    VnExpressFeed("du-lich", "https://vnexpress.net/rss/du-lich.rss"),
    VnExpressFeed("oto-xe-may", "https://vnexpress.net/rss/oto-xe-may.rss"),
    VnExpressFeed("y-kien", "https://vnexpress.net/rss/y-kien.rss"),
    VnExpressFeed("tam-su", "https://vnexpress.net/rss/tam-su.rss"),
    VnExpressFeed("cuoi", "https://vnexpress.net/rss/cuoi.rss"),
    VnExpressFeed("tin-xem-nhieu", "https://vnexpress.net/rss/tin-xem-nhieu.rss"),
)

DEFAULT_FEED_URLS: tuple[str, ...] = tuple(feed.url for feed in DEFAULT_FEEDS)
# Kept for callers/tests that still refer to the original demo feed.
DEFAULT_FEED_URL = "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"

_FEED_BY_URL = {feed.url: feed for feed in DEFAULT_FEEDS}

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
    feed_url: str = DEFAULT_FEED_URL
    category: str = "khoa-hoc-cong-nghe"


def category_for_feed_url(feed_url: str) -> str:
    known = _FEED_BY_URL.get(feed_url)
    if known is not None:
        return known.category
    path = urlsplit(feed_url).path.rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    if slug.endswith(".rss"):
        slug = slug[: -len(".rss")]
    return slug or "vnexpress"


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
        return self.fetch_documents_from_feeds([self._feed_url])

    def fetch_documents_from_feeds(self, feed_urls: Sequence[str]) -> list[SourceDocument]:
        """Fetch many RSS channels, dedupe by article URL, then extract bodies."""

        if not feed_urls:
            msg = "feed_urls must not be empty"
            raise ValueError(msg)

        unique_items: dict[str, RssItem] = {}
        for feed_url in feed_urls:
            response = self._http.get(feed_url)
            for item in self.parse_feed(response.text, feed_url=feed_url):
                # First feed that discovers a URL wins (tin-moi-nhat is listed first).
                unique_items.setdefault(item.link, item)

        documents: list[SourceDocument] = []
        for item in unique_items.values():
            try:
                article = self._http.get(item.link)
                documents.append(self.build_document(item, article_html=article.text))
            except Exception as exc:
                # Multi-feed runs hit video/live/paywall pages; skip one bad URL
                # instead of failing the whole catalog fetch.
                logger.warning(
                    "vnexpress_article_skipped",
                    extra={"url": item.link, "category": item.category, "error": type(exc).__name__},
                )
                continue
        return documents

    def parse_feed(self, xml_text: str, *, feed_url: str | None = None) -> list[RssItem]:
        resolved_feed = feed_url or self._feed_url
        category = category_for_feed_url(resolved_feed)
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
                    feed_url=resolved_feed,
                    category=category,
                )
            )
        return items

    def build_document(self, item: RssItem, *, article_html: str) -> SourceDocument:
        text = extract_article_text(article_html)
        metadata: dict[str, Any] = {
            "feed_url": item.feed_url,
            "category": item.category,
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
