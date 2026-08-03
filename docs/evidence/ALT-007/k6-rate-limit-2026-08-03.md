# ALT-007 — Envoy rate-limit spike alert

## Trigger thật

Rate-limit k6 run ngày `2026-08-03` tạo 5 response 429; không tạo API/DB/
Prefect failure giả. Rule provisioned có điều kiện `increase(...[5m]) >= 5`,
nhãn `alert_receiver=slack` và `severity=warning`.

## Runtime evidence

- `2026-08-03T08:22:49.245Z`: Alertmanager API báo
  `KubeRagEnvoyRateLimitSpike` `active`.
- `2026-08-03T08:23:54Z`: Prometheus trả
  `ALERTS{alertname="KubeRagEnvoyRateLimitSpike",alertstate="firing"} = 1`.
- Alertmanager annotations có summary “Envoy returned at least five
  rate-limited responses in five minutes” và runbook Git-tracked.
- `2026-08-03T08:25:13Z`: aggregate
  `alertmanager_notifications_total{integration="slack"}` là `5`, còn
  `alertmanager_notifications_failed_total{integration="slack"}` là `0`.
- `2026-08-03T08:30:08Z`: Prometheus không còn series `ALERTS` của alert này
  và Alertmanager API không còn alert active. Alert đã tự resolve sau khi
  cửa sổ `increase(...[5m])` hết hiệu lực.
- Sau resolved, aggregate Slack notification total là `6`, còn failed total
  vẫn là `0`.

Metric notification là aggregate của Alertmanager, nên nó chứng minh Slack
integration không báo failure tại snapshot nhưng không thay thế ảnh UI cho
từng message. Ảnh Slack Firing/Resolved của alert rate-limit và Grafana panel
là artefact bổ sung còn cần operator chụp; link Alertmanager nội bộ vẫn pending
và không được public hóa.
