# ALT-008 — Real ingestion-alert lifecycle

The controlled Prefect failure documented in
[`ING-011`](../ING-011/gcp-ingestion-failure-alert-2026-08-03.md) produced the
real `KubeRagIngestionFailed` alert, rather than a synthetic rule.

- Prometheus recorded it as `firing` at `2026-08-03T10:53:38Z`.
- Alertmanager routed it to `slack`.
- After the 30-minute timestamp lookback, Prometheus and Alertmanager both
  returned no active alert.
- The aggregate Slack notification counter moved from `10` to `12`; all
  Slack delivery-failure counters remained `0`.

No alert, metric, Pod, database row, or PVC was manually removed to cause the
Resolved state.
