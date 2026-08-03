ING-010 Embedding batch

Evidence layers:

1. Offline interface + fake:
   `uv run pytest apps/ingestion/tests/unit/test_embedding.py -q --no-cov`
2. GCP real model smoke:
   `docs/evidence/ING-010/gcp-e5-smoke.txt`

What passed on GCP:

- Downloaded `intfloat/multilingual-e5-small` onto PVC `kuberag-embedding-models`
- Sample batch embed returned 384-dim vectors with measured load/embed latency and RSS
- Prefect worker set to `KUBERAG_EMBEDDING_MODE=e5` with local-only cache mount

Still deferred:

- Full live Prefect flow upsert into PostgreSQL (user skipped fake-embed DB path; real-e5 flow run can be a later checkpoint)
