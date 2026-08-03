# PERF-003 — correlated observability window

## Mốc thời gian thực tế

| UTC | Quan sát |
| --- | --- |
| `08:19:16` | Sau RAG load: node 4% CPU, 30% RAM; 74,74 API requests trong cửa sổ Prometheus 5 phút, 0 Envoy rate-limit. |
| `08:22:55` | Sau status burst: Prometheus tăng rate-limit 5,1664 trong cửa sổ 5 phút; Alertmanager có alert active. |
| `08:23:54` | Prometheus `ALERTS{alertname="KubeRagEnvoyRateLimitSpike",alertstate="firing"}` bằng 1. Node 5% CPU, 30% RAM. |
| `08:25:13` | Target Envoy và RAG API đều `up=1`; mọi PVC `Bound`; Slack notification failure total bằng 0. |

## Prometheus snapshot

- Targets `up=1`:
  - `kuberag-envoy-metrics` tại Envoy data plane.
  - `kuberag-rag-api` tại FastAPI.
- `sum(rate(kuberag_api_requests_total[5m])) = 0,2211 request/s` tại thời
  điểm sau test; cửa sổ này có cả traffic status/RAG ngoài scenario, nên không
  được dùng thay cho throughput chính xác của k6.
- 5xx trong cửa sổ: không có series trả về từ
  `sum(increase(kuberag_api_requests_total{status_code=~"5.."}[5m]))`.
- Histogram service-wide tại snapshot: p50 `0,005 s`, p95 `0,0095 s`, p99
  `0,0099 s`. Giá trị này bị chi phối bởi `/status` nhẹ và không thay thế p95
  end-to-end RAG `2,458 s` trong `PERF-001`.
- RAG-stage counter không tăng trong cửa sổ sau cùng vì đó là rate-limit
  status scenario; đây phù hợp với thiết kế không gọi LLM.

## Resource và persistence sau test

- Node: `432m` CPU (5%), `4.860 MiB` RAM (30%).
- RAG pods: API `20m` CPU / `746 MiB`, llama.cpp `1m` / `841 MiB` tại sample
  sau test.
- Prefect: server `27m` / `174 MiB`, worker `4m` / `85 MiB`.
- Pod query không trả Pod phase khác `Running`/`Succeeded`; không có restart
  mới trong snapshot observability. Tất cả 10 PVC hiển thị `Bound`.

Chưa có Grafana screenshot trong evidence này. Prometheus và Alertmanager API
output là evidence runtime có thể tái tạo qua IAP port-forward; ảnh dashboard
vẫn là artefact bổ sung cần chụp thủ công nếu acceptance yêu cầu UI trực quan.

