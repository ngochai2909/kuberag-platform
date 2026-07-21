# Agent evaluations

`cases.jsonl` is the seed regression dataset for behavior that cannot be proven by unit tests
alone. Every line is a standalone JSON object so it can be uploaded to LangSmith or consumed by
another evaluation runner.

For each prompt/model change:

1. Run deterministic unit and integration tests first.
2. Execute these cases against the candidate and current baseline.
3. Score final-answer correctness, required tool trajectory, safety, latency, and token usage.
4. Review failures manually before accepting an LLM-as-judge score.
5. Add sanitized production failures as new regression cases; never copy secrets or PII.

The repository intentionally does not run model-backed evals in normal CI because that would make
tests non-deterministic and incur external cost. Add a separately authorized workflow when the
project has an evaluation account and budget.
