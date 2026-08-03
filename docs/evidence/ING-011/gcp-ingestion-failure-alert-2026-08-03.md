# ING-011 — Controlled ingestion failure telemetry and alert

## Scope and safety

At approximately 2026-08-03 10:52 UTC (the Job log timestamp), the operator ran
`make gcp-release-ingestion-failure-test` after the reviewed release manifest
had rolled out successfully. The test-only Job used
`http://127.0.0.1:1/kuberag-rss-failure-test` **inside its own Pod**. The
connection was refused before document retrieval, so it did not contact
VnExpress or perform normalize, chunk, embed, or pgvector upsert work.

The Job reached the expected Kubernetes `Failed` state after Prefect retried
the fetch task twice. Its flow run was
`3cfbbdb8-0627-462d-9fa5-dd98c818864f` (`merry-stork`).

## Runtime telemetry

- Loki returned an `ERROR` log for this flow/task with
  `service_name=kuberag-ingestion`, `flow_run_id` above, and trace ID
  `80f65092f2bc8a699bc3b717ee99644b`. The event reports the expected
  connection-refused failure after retries; exception stack content is not
  copied into this evidence.
- Tempo search for `service.name = kuberag-ingestion` returned that same trace,
  whose root span was `fetch-vnexpress-903`. It contained four spans, all
  marked error, over about 2.6 seconds.
- Prometheus scraped
  `kuberag_ingestion_last_failure_timestamp_seconds{status="failed"}` with
  value `1785754359.5166485`.

This proves the failure crossed the expected path:

```text
test-only Prefect Job -> OTel Collector -> Loki / Tempo / Prometheus -> Alertmanager
```

## Alert result

Prometheus reported `KubeRagIngestionFailed` as `firing` at
`2026-08-03T10:53:38Z`. Alertmanager reported the same alert `active`, routed
to receiver `slack`, with the Git-tracked alerting runbook annotation.

After the 30-second Alertmanager group wait, the scraped Slack integration
metrics were:

- `alertmanager_notifications_total{integration="slack"} = 10`
- every `alertmanager_notifications_failed_total{integration="slack",...} = 0`

The notification counter is aggregate, so it demonstrates successful
Alertmanager-to-Slack delivery without asserting a per-message Slack UI
screenshot. The alert remains expected to resolve once the rule's 30-minute
timestamp window expires; no metric, database row, Pod, or alert was manually
deleted to force resolution.
