# NET-006 — k6 Envoy rate-limit verification

`tests/k6/rate-limit.js` đã chạy qua Envoy public gateway ngày
`2026-08-03` và gửi 15 `GET /api/v1/status` sau quota reset.

- 10 response 2xx và 5 response 429 (k6 custom counter).
- 30/30 checks pass: status chỉ là 2xx/429, không có 5xx.
- Prometheus metric Envoy `increase(...rate_limited[5m])` = 5,1664 trong cửa
  sổ sample sau run.

Điều này đóng evidence runtime cho giới hạn rate của Envoy, thay thế smoke curl
trước đó. Summary chi tiết: `../PERF-001/rate-limit-summary.json`.

