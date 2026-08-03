# PERF-004 — latency và error report

Nguồn số liệu là hai k6 summary JSON được tạo bởi run thực tế ngày
`2026-08-03`; không có dữ liệu mô phỏng.

| Scenario | p50 | p95 | max | HTTP failure | 5xx | Ghi chú |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| RAG load | 1,208 s | 2,458 s | 2,730 s | 0/9 | 0/9 | Query thực qua Envoy, có answer/source/correlation IDs. |
| Rate limit status | 111,38 ms | 114,91 ms | 114,91 ms | 0/15 | 0/15 | 5/15 là expected 429 từ Envoy. |

RAG load đạt threshold p95 `<55 s` và failure `<5%`. Burst rate-limit đạt
`http_req_failed == 0` vì 429 là kết quả mong đợi của scenario, không phải lỗi
ứng dụng.

