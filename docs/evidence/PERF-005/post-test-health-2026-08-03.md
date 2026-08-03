# PERF-005 — post-test health

Kiểm tra sau cả hai scenario:

- k6 load không kích hoạt abort threshold `rag_load_failures >20%`.
- k6 rate-limit chỉ dùng `GET /api/v1/status`; không chạy RAG/LLM và không
  thay đổi database hay Prefect flow.
- Node sau alert Firing: `5%` CPU, `30%` RAM, thấp hơn stop condition 85%.
- Envoy, RAG API, Alertmanager, Prometheus, Loki, Tempo, Pyroscope và OTel
  Collector đều Ready; restart count trong snapshot là 0.
- Toàn bộ PVC là `Bound`.
- Targets Envoy metrics và RAG API là `up=1`.

Kết luận: hai test không làm hỏng dữ liệu hay cluster trong snapshot kiểm
chứng. Đây là kiểm chứng single-node bounded load, không phải chaos test.

