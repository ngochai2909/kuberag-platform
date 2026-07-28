# Data Model And Ingestion Contract

Status: design decision for the data-layer phase. This is a logical model, not
an Alembic migration or a deployed PostgreSQL schema.

## Purpose And Scope

KubeRAG ingests two required source types: VnExpress RSS and the NVD CVE API.
Their raw formats differ, so source adapters must normalize both into one
document contract before PostgreSQL, chunking, and embedding are involved.

```text
VnExpress RSS / NVD API
-> source adapter
-> SourceDocument
-> documents
-> chunks + embeddings
-> RAG retrieval and source links
```

The initial implementation starts with VnExpress. NVD-specific metadata is
deferred until its API sample is inspected, but it must conform to the same
`SourceDocument` contract.

## VnExpress Source Decision

Initial feed:

```text
https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss
```

The technology/science feed is a better initial RAG corpus than the general
"Tin mới nhất" feed: it is closer to the platform's technical focus, keeps the
corpus smaller, and avoids discovering the same article from both a general and
a category feed.

RSS is used to discover articles and obtain metadata. It is not treated as the
full article body because its `description` is a short HTML summary. For a new
article, the adapter fetches the canonical article URL and extracts readable
text from the article content area. If extraction fails, the adapter records a
failure or, for an explicitly configured fallback, uses the cleaned RSS summary
without pretending it is the full article.

VnExpress publishes the feed list and RSS terms at
<https://vnexpress.net/rss/>. The application must retain the canonical source
URL and show a clear `VnExpress` attribution with every answer source. It must
not expose raw full articles through its own API or logs.

## SourceDocument Contract

Every adapter returns this normalized logical object:

```text
source: string
external_id: string
title: string
url: string
published_at: timestamp with timezone | null
text: string
checksum: sha256 hex string
metadata: JSON object
```

For VnExpress, map the RSS/article data as follows:

| Source field | SourceDocument field | Rule |
|---|---|---|
| RSS `guid` / canonical `link` | `external_id` | Use the normalized canonical article URL. This is stable enough for the initial source and directly supports deduplication. |
| RSS `title` | `title` | Trim and normalize whitespace. |
| RSS `link` | `url` | Preserve the canonical VnExpress URL for the frontend source link. |
| RSS `pubDate` | `published_at` | Parse as a timezone-aware timestamp. |
| Article body | `text` | Extract readable text, normalize whitespace, and exclude navigation, images, scripts, and captions unless intentionally retained later. |
| RSS HTML `description` | `metadata.summary` | Strip HTML before storage; do not use it as the normal full-text corpus. |
| RSS `enclosure.url` | `metadata.image_url` | Optional display metadata only; images are not embedded in this phase. |
| Feed URL | `metadata.feed_url` | Records which configured feed discovered the article. |
| Extractor revision | `metadata.extraction_version` | Allows a future extractor change to be traced. |

The checksum is calculated from the normalized title and full text, not the raw
RSS XML. This detects an edited article even when its URL remains unchanged.

## Logical Database Model

### `documents`

One row represents one source article or CVE record.

| Field | Purpose |
|---|---|
| `id` | Internal UUID primary key. |
| `source` | Source identifier such as `vnexpress` or `nvd`. |
| `external_id` | Stable identity supplied or derived by the source. |
| `title` | Human-readable source title. |
| `url` | Canonical URL returned to the user as a clickable source. |
| `published_at` | Source publication time when available. |
| `content` | Normalized full text used to create chunks. |
| `checksum` | SHA-256 of normalized content for change detection. |
| `metadata` | Source-specific JSONB metadata. |
| `created_at`, `updated_at` | Database audit timestamps. |

Required constraint:

```text
UNIQUE (source, external_id)
```

This means discovering the same VnExpress URL through a second feed cannot
create a second document.

### `chunks`

One document produces zero or more chunks for retrieval.

| Field | Purpose |
|---|---|
| `id` | Internal UUID primary key. |
| `document_id` | Foreign key to `documents.id`. |
| `chunk_index` | Deterministic order inside a document. |
| `content` | Text segment passed to the embedding model. |
| `embedding` | pgvector value for semantic retrieval. |
| `metadata` | Chunk-level data such as character offsets or tokenizer version. |
| `created_at`, `updated_at` | Database audit timestamps. |

Required constraint:

```text
UNIQUE (document_id, chunk_index)
```

The vector dimension and index type are intentionally not fixed yet. They must
be chosen after the embedding model is pinned; an Alembic migration cannot
safely declare `vector(N)` until `N` is known.

### `ingestion_runs`

One row records the KubeRAG business result of one ingestion execution. It is
not a duplicate of Prefect's own internal state: it records source-specific
counts, watermarks, and errors needed for dashboards and alerting.

| Field | Purpose |
|---|---|
| `id` | Internal UUID primary key. |
| `prefect_flow_run_id` | Optional external link to the Prefect run. |
| `flow_name` | Stable flow identifier. |
| `source_scope` | Feed/API scope processed by this run. |
| `status` | `running`, `completed`, `failed`, or another controlled lifecycle value. |
| `watermark_from`, `watermark_to` | Window used to select new or updated records. |
| `fetched_count`, `inserted_count`, `updated_count`, `skipped_count`, `failed_count` | Operational counters. |
| `error_summary` | Bounded and sanitized error context; never raw article content or credentials. |
| `started_at`, `finished_at` | Execution timing. |

## Ingestion And Deduplication Rules

```text
1. Fetch configured RSS feed with timeout and retry/backoff.
2. Parse entries and normalize each canonical URL.
3. Check documents by (source, external_id).
4. For a new or recently changed candidate, fetch the article page at a low,
   bounded concurrency.
5. Extract and normalize text, then calculate checksum.
6. If the checksum is unchanged, increment skipped_count and do not re-embed.
7. If new or changed, upsert documents, replace affected chunks, and embed.
8. Complete ingestion_runs with counters and its final watermark.
```

The initial schedule should be conservative. RSS is an update feed, not an
historical archive, and the adapter should not retry indefinitely or fetch pages
at high parallelism. Exact schedule, timeout, retry count, chunk size, and
embedding batch size remain implementation decisions to measure on the 16 GiB
single-node environment.

## RAG Source Links

Retrieval returns chunks, but the API joins each selected chunk back to its
`documents` row. A response source is derived from document-level fields:

```json
{
  "title": "Article title",
  "url": "https://vnexpress.net/example.html",
  "source": "vnexpress",
  "score": 0.87
}
```

The frontend displays `title` as the link label and `url` as the destination.
Several retrieved chunks from one document should normally be deduplicated into
one displayed source entry.

## Test Fixture And Data Handling Policy

- Unit tests use a small XML fixture and synthetic article HTML, not live RSS.
- Fixtures contain only the minimum non-sensitive sample content needed to test
  parsing and extraction.
- Runtime logs contain IDs, counts, and sanitized errors; they do not contain
  full articles, prompts, database URLs, or credentials.
- Raw RSS XML and raw article HTML are not stored in PostgreSQL in the first
  milestone. The normalized text, canonical URL, checksum, and bounded metadata
  are sufficient for retrieval and traceability.

## Decisions Still Pending

- Inspect an NVD API sample and define its `external_id` and metadata mapping.
- Pin the embedding model and its vector dimension.
- Choose chunking strategy, chunk size, overlap, and tokenizer behavior.
- Choose pgvector index type and create it only after a representative corpus
  and query behavior are measured.
- Decide whether source-specific per-record error history requires a future
  `ingestion_errors` table. It is not needed for the first milestone.
