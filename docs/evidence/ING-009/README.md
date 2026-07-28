ING-009 Chunk size/overlap boundary tests

Verification:
  uv run pytest apps/ingestion/tests/unit/test_chunking.py -q

Result: Pass on 2026-07-28.

Strategy: sentence-aware packing with configurable max_chars/overlap_chars,
optional title prefix on every chunk, hard-split only when a single sentence
exceeds the budget. No embedding model is loaded.

Defaults: max_chars=800, overlap_chars=150, version=sentence-overlap-v1.
