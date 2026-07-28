ING-010 Embedding batch (offline interface + fake)

Verification:
  uv run pytest apps/ingestion/tests/unit/test_embedding.py -q --no-cov

Result: Pass on 2026-07-28 for the offline path.

What this proves:
- `EmbeddingProvider` contract (`embed_documents` batching, `embed_query`)
- `FakeEmbeddingProvider` returns 384-dim L2-normalized vectors without downloading a model
- Upsert path stores embeddings when an embedder is injected

What this does not yet prove:
- Real `intfloat/multilingual-e5-small` CPU/RAM/latency on the GCP VM
- That evidence waits for the ingestion image/Prefect worker deploy
