# KubeRAG evaluations

`cases.jsonl` is the seed regression dataset for RAG behavior that cannot be proven by unit tests alone. Every line is a standalone JSON object so it can be consumed by a future deterministic or model-backed evaluation runner.

For each prompt or retrieval change:

1. Run deterministic unit and integration tests first.
2. Execute these cases against the candidate and current baseline when an evaluation runner exists.
3. Score answer grounding, source use, prompt-injection resistance, safety, latency, and resource usage.
4. Review failures manually before accepting any automated judge score.
5. Add sanitized production failures as new regression cases; never copy secrets or PII.

The repository intentionally does not run model-backed evals in normal CI because that would make tests non-deterministic and may incur external cost. The required demo path uses self-hosted llama.cpp, not an external LLM API.
