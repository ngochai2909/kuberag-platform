# PERF-002 — k6 rate-limit run

## Phạm vi

- Script: `tests/k6/rate-limit.js`.
- Đích: `GET /api/v1/status` qua Envoy public gateway đã redacted; endpoint
  nhẹ này không gọi llama.cpp, embedding hay PostgreSQL.
- Script chờ 65 giây cho quota window mới, sau đó gửi chính xác 15 iterations
  chung với tối đa 15 VU.
- `429` được khai báo là expected response cho scenario này; 5xx và các status
  khác vẫn là lỗi.
- Output gốc: `../PERF-001/rate-limit-summary.json` (Makefile dùng chung thư
  mục summary).

## Kết quả thực tế

Summary được thu lúc `2026-08-03T08:22:55Z`.

| Metric | Kết quả | Điều kiện | Kết luận |
| --- | ---: | ---: | --- |
| HTTP requests / iterations | 15 / 15 | 15 | Pass |
| Response hợp lệ | 30/30 checks | chỉ 2xx hoặc 429; không 5xx | Pass |
| Envoy 429 | 5 | ít nhất 1 | Pass |
| HTTP failure | 0% (0/15) | 0% | Pass |
| Unexpected status | 0% (0/15) | 0% | Pass |
| HTTP p95 | 114,9 ms | — | Ghi nhận |

Prometheus ngay sau test trả về
`sum(increase(envoy_http_local_rate_limit_rate_limited[5m])) = 5,1664`.
Sai số phần thập phân là do Prometheus `increase()` ngoại suy theo sample
boundary; k6 đếm chính xác 5 response `429`.

Không có request RAG trong scenario này và không có 5xx.

