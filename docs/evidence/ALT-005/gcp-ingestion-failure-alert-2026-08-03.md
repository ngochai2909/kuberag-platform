# ALT-005 — Ingestion failure Slack alert

See the shared runtime evidence at
[`ING-011`](../ING-011/gcp-ingestion-failure-alert-2026-08-03.md).

The controlled Prefect failure produced `KubeRagIngestionFailed` in
Prometheus and an active Alertmanager alert with receiver `slack`. The Slack
delivery failure counters were zero at the post-notification snapshot. The
alert is intentionally allowed to resolve naturally after its 30-minute
lookback window.

