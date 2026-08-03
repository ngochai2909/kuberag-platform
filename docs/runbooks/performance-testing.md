# k6 performance and rate-limit checkpoint

## Mục tiêu

k6 là client tạo HTTP workload qua Envoy, không chạy trong FastAPI hay gọi Pod
trực tiếp. Hai luồng cần quan sát cùng một thời điểm là:

```text
k6 -> Envoy Gateway -> FastAPI -> E5 -> PostgreSQL/pgvector -> llama.cpp
k6 -> Envoy Gateway -> /api/v1/status   (rate-limit only, no LLM)
```

`tests/k6/load.js` ramp 1→2→3 VU, mỗi VU nghỉ 35 giây. Với giới hạn Envoy
chung 10 request/phút và một data-plane Pod, đây là tải demo an toàn hơn tải
đồng thời dày đặc; threshold là failure <5% và p95 <55 giây. Test tự dừng nếu
failure vượt 20% sau 35 giây. `tests/k6/rate-limit.js` chờ 65 giây cho quota
mới rồi burst đúng 15 request vào `/api/v1/status`; chỉ `2xx` hoặc `429` hợp lệ
và phải có ít nhất một `429`, không có `5xx`.

## Checkpoint trước khi chạy

Đây là tải lên Envoy/llama.cpp và có thể tiêu thụ quota 10 request/phút; không
chạy khi Gate 0 chưa có snapshot ổn định 30 phút. Trước khi được xác nhận, chỉ
kiểm tra local:

```bash
k6 inspect tests/k6/load.js
k6 inspect tests/k6/rate-limit.js
```

Ngay trước run đã được xác nhận, chụp đầu kỳ: node/Pod/PVC/restarts,
`kubectl top`, disk/PVC usage và Prometheus targets. Dừng nếu node memory >85%,
workload >90% limit, hoặc Tempo/Loki/Collector restart.

## Chạy và lưu evidence

```bash
make k6-load K6_GATEWAY_URL=http://VM_EXTERNAL_IP:8080
make k6-rate-limit K6_GATEWAY_URL=http://VM_EXTERNAL_IP:8080
```

`K6_GATEWAY_URL` là URL Envoy đã giới hạn firewall, không phải ClusterIP hay
Pod IP. Hai lệnh ghi JSON vào `docs/evidence/PERF-001/`; chỉ commit summary đã
redact endpoint public nếu cần. Trong cùng time window, lưu Grafana screenshot
RPS, p50/p95/p99, status/error, Envoy 429 (sau khi Envoy scrape được xác minh),
CPU/RAM/restarts và RAG-stage duration. Lưu health cuối kỳ tại
`docs/evidence/PERF-003/` và kết luận safe demo load/bottleneck ở `PERF-006`.
