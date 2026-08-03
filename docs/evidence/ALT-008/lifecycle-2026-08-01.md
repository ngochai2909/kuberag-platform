# ALT-008 — Alertmanager Slack lifecycle

Ngày 2026-08-01, rule test-only `KubeRagAlertLifecycleTest` với biểu thức
`vector(1)` và `for: 30s` được áp dụng vào namespace `observability`.

- Prometheus Rules API báo `state: firing`, `health: ok`.
- Alertmanager API báo alert `active` với label `alert_receiver=slack`.
- Slack đã hiển thị thông báo `[FIRING:1] KubeRagAlertLifecycleTest`.
- Sau khi xóa rule test-only, Prometheus không còn trả alert đó và Alertmanager
  không còn alert active.
- Metric `alertmanager_notifications_total{integration="slack"}` tăng lên `2`;
  mọi series `alertmanager_notifications_failed_total{integration="slack"}` là
  `0`. Đây là bằng chứng hai notification Firing và Resolved được gửi thành
  công.

Không có API RAG, Prefect flow, PostgreSQL hay workload lỗi thật nào được tạo
trong test này. Slack webhook không xuất hiện trong evidence.
