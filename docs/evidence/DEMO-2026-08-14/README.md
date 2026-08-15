# KubeRAG runtime flow and telemetry evidence — 2026-08-14

This evidence set was captured from the GCP k3s deployment on 2026-08-14.
No credential, bearer token, kubeconfig, database URL, or Terraform state is
stored in this directory.

## Result

| Criterion | Result | Runtime evidence |
| --- | --- | --- |
| TC1 — service logs | PASS | RAG API and ingestion logs are queryable in Loki. The RAG log contains matching request and trace identifiers. |
| TC2 — metrics/dashboard | PASS | Prometheus had 26/26 healthy scrape targets. Grafana Overview/Operations rendered request, RAG-stage, resource, PVC, restart, Envoy, and Loki panels. |
| TC3 — RAG trace | PASS | Tempo returned one five-span trace covering HTTP, embedding, pgvector retrieval, prompt construction, and llama.cpp generation. |
| TC4 — alerting | PASS | Seven KubeRAG rules were healthy and Normal; Alertmanager had no active alert. The prior controlled lifecycle evidence proves Pending/Firing/Resolved and Slack delivery. |
| TC5 — ingest/retrieval | PASS | The latest Prefect run completed, ingestion exported 1,017 completed documents, and a real UI query returned three pgvector-backed sources with `top_k=3`. |

## End-to-end paths exercised

```text
Browser -> SSH tunnel -> Envoy NodePort -> HTTPRoute -> FastAPI
        -> query embedding -> PostgreSQL/pgvector -> bounded prompt
        -> llama.cpp -> answer + 3 sources

Prefect daily deployment -> ingest-vnexpress task -> watermark/idempotency
        -> embedding/upsert -> PostgreSQL/pgvector

FastAPI/ingestion -> OTel Collector -> Loki/Tempo
FastAPI/Kubernetes/Envoy/OTel -> Prometheus -> Grafana
FastAPI Pyroscope SDK -> Pyroscope
Prometheus rules -> Alertmanager -> Slack route
```

## TC1 — logs

- [RAG API LogQL result](screenshots/grafana-loki-request-log.png) shows one
  `request_completed` entry for request
  `19414e71-4472-4b88-bd3f-773621355ca5`.
- [RAG log/trace correlation](screenshots/grafana-loki-trace-correlation.png)
  shows `status_code=200` and trace
  `2aa8bf96e221e53c5e727ef536372916` in structured metadata.
- [Ingestion logs](screenshots/grafana-loki-ingestion-logs.png) show one
  completed flow event and five idempotent `vnexpress_article_skipped` events.
- Machine-readable query results are in [loki-ui-request.json](loki-ui-request.json)
  and [loki-ingestion-recent.json](loki-ingestion-recent.json).

## TC2 — metrics and dashboards

- [Grafana Overview](screenshots/grafana-overview.png) covers RPS, API p95,
  status codes, RAG stages, application memory, restarts, Envoy status classes,
  and rate-limit rejections.
- [Grafana Operations — upper section](screenshots/grafana-operations.png) shows
  `200` outcomes, zero errors, warm-up readiness, and telemetry scrape health.
- [Grafana Operations — lower section](screenshots/grafana-operations-lower.png)
  shows CPU, memory, PVC usage, restarts, node utilization, and recent Loki
  events.
- [Prometheus ingestion metric](screenshots/grafana-prometheus-ingestion-metric.png)
  shows `kuberag_ingestion_documents_total{status="completed"}=1017` using
  `last_over_time(...[8h])`.
- [Prometheus target health](screenshots/prometheus-targets.png) visually shows
  the Envoy scrape target up. The API inventory in
  [prometheus-targets.json](prometheus-targets.json) contains 26 active targets,
  all 26 healthy.
- RAG-stage p95 at capture time was approximately retrieval `0.2425s`, prompt
  `0.0095s`, and generation `29s`; the UI-warmed request below completed much
  faster at `4.947s` total.

The ingestion instant-vector queries were empty after the OTel Collector
restart, while historical samples remained queryable. The authoritative
eight-hour samples are stored in
[prometheus-ingestion-documents-last-8h.json](prometheus-ingestion-documents-last-8h.json),
[prometheus-ingestion-runs-last-8h.json](prometheus-ingestion-runs-last-8h.json),
and [prometheus-ingestion-duration-last-8h.json](prometheus-ingestion-duration-last-8h.json).

## TC3 — trace

- [Tempo trace table](screenshots/grafana-tempo-trace.png) finds the trace by
  TraceQL.
- [Tempo trace detail](screenshots/grafana-tempo-trace-detail.png) shows one
  `POST 200` trace with five spans:
  `http.request`, `rag.embed_query`, `rag.pgvector_search`,
  `rag.build_prompt`, and `rag.llm_generate`.
- The UI trace duration was `4.95s`; generation accounted for about `4.8s`.
- Machine-readable trace data is in [tempo-ui-trace.json](tempo-ui-trace.json).

## TC4 — alerts

- [Grafana alert rule list](screenshots/grafana-alert-rules-list.png) shows all
  seven KubeRAG rules in the Normal state.
- [Alertmanager](screenshots/alertmanager-alerts.png) shows no active alert
  group at capture time, which is the expected healthy state.
- [prometheus-alert-rules.json](prometheus-alert-rules.json) records all seven
  rules with `health=ok`; [alertmanager-active-alerts.json](alertmanager-active-alerts.json)
  records zero active alerts.
- The alert was deliberately not fired again during this capture to avoid a
  duplicate Slack notification. The real controlled Pending -> Firing ->
  Resolved lifecycle and Slack delivery remain documented in
  [../ALT-008/ingestion-failure-lifecycle-2026-08-03.md](../ALT-008/ingestion-failure-lifecycle-2026-08-03.md).

## TC5 — ingest and retrieval

- [Prefect flow run](screenshots/prefect-flow-run.png) shows flow
  `kuberag-daily-ingest`, deployment `daily`, task `ingest-vnexpress-e2a`,
  state `Completed`, duration `33m49s`, and a clean worker exit.
- [prefect-latest-flow-runs.json](prefect-latest-flow-runs.json) and
  [prefect-latest-flow-logs.json](prefect-latest-flow-logs.json) contain the
  API evidence for that run. The deployment is active with cron
  `0 3 * * *` UTC.
- [News browse UI](screenshots/frontend-news-browse.png) shows the live catalog
  and category counts.
- [RAG chat UI](screenshots/frontend-chat-answer.png) shows a real answer,
  three source cards, thumbnails, `top_k=3`, `4947.24ms` total latency, and the
  request/trace identifiers used for Loki and Tempo correlation.
- [frontend-response-meta.json](frontend-response-meta.json) stores only the
  non-sensitive timing and correlation metadata.
- An additional direct API run is stored in [rag-response.json](rag-response.json);
  it returned HTTP 200 and three sources in `28.55s` before llama.cpp was warm.

## Additional telemetry — profiling

- [Pyroscope CPU profile](screenshots/pyroscope-ui.png) shows the
  `kuberag-rag-api` CPU timeline and flamegraph/top table for the last hour.
- [pyroscope-rag-api-profile.json](pyroscope-rag-api-profile.json) contains a
  valid 38-level flamebearer profile with 176 frame names.

## Operational notes

- `kubectl port-forward` directly to the Envoy LoadBalancer service timed out,
  but Envoy itself was healthy: in-cluster ClusterIP and NodePort requests both
  returned HTTP 200. The browser flow was therefore captured through an SSH
  tunnel to the Envoy NodePort, preserving the real Envoy/HTTPRoute path.
- The latest Prefect run was shown as starting `6h41m` late. This is consistent
  with a cost-controlled VM/cluster that was unavailable at the scheduled
  `03:00 UTC` time and executed the scheduled run after startup. The run still
  completed successfully.
- Alertmanager reports cluster mode disabled because this environment uses a
  single Alertmanager replica; that is expected for the temporary constrained
  deployment.
