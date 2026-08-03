# GCP Observability Single-Node

## Mục tiêu

Stack observability trả lời bốn câu hỏi khác nhau mà chỉ `kubectl logs` không
trả lời được:

```text
Prometheus: bao nhiêu request, latency bao lâu, Pod dùng bao nhiêu CPU/RAM?
Loki: request X đã xảy ra gì, status nào, trong bao lâu?
Tempo: request X đi qua API -> embed -> retrieve -> LLM theo thứ tự nào?
Pyroscope: CPU đang tốn ở chính dòng/hàm nào trong process Python?
```

Luồng hiện tại:

```text
FastAPI / Prefect --OTLP--> OTel Collector --logs--> Loki
                                      \--traces-> Tempo
FastAPI / Prefect --/metrics---------> Prometheus
FastAPI --Pyroscope SDK--------------> Pyroscope
Grafana -----------------------------> four data sources above
```

`OTLP` là OpenTelemetry Protocol. Collector là gateway nội bộ: ứng dụng chỉ
biết một địa chỉ Collector, còn Collector định tuyến log sang Loki và trace
sang Tempo. Pyroscope nhận profile trực tiếp theo yêu cầu kiến trúc, không dùng
eBPF, `hostPath`, privileged Pod hay Grafana Alloy.

## Trạng thái và an toàn

Các Service đều là `ClusterIP`: chỉ Pod trong cluster truy cập được. Không có
port observability nào public qua Envoy hay GCP firewall. Grafana dùng tài khoản
trong Secret Kubernetes và chỉ được mở tạm trên `127.0.0.1` của laptop.

Trên single-node, resource/PVC/retention được cố ý giới hạn để không cạnh tranh
với PostgreSQL, E5 và llama.cpp:

| Thành phần | PVC | Retention | Memory limit |
|---|---:|---:|---:|
| Prometheus | 10 GiB | 3 ngày hoặc 8 GB | 1 GiB |
| Loki | 5 GiB | 72 giờ | 512 MiB |
| Tempo | 5 GiB | 48 giờ | 768 MiB |
| Pyroscope | 5 GiB | theo dung lượng PVC | 384 MiB |
| Grafana | 2 GiB | cấu hình/dashboards | 384 MiB |

Budget alert không phải là spend cap. Theo dõi `kubectl top`, PVC và disk VM
trước khi tăng retention hoặc chạy k6.

## Cài đặt và render

`make gcp-observability-render` chỉ render Helm/Kustomize tại local. Nó không
thay đổi cluster. `make gcp-observability-install` cài/upgrade Helm releases và
`make gcp-observability-apply` tạo ServiceMonitor/dashboard ConfigMap; hai lệnh
sau thay đổi cluster nhưng không tạo VM, firewall hay IP.

```bash
make gcp-k3s-tunnel                 # Terminal A, giữ mở
make gcp-observability-render       # Terminal B, read-only local
make gcp-observability-install      # thay đổi Kubernetes workloads/PVCs
make gcp-observability-apply        # thay đổi Kubernetes resources
make gcp-observability-status       # read-only
```

Expected status là các Pod `Running` và PVC `Bound`. Nếu một Pod Pending, xem
`kubectl -n observability describe pod POD_NAME`; trên single-node nguyên nhân
phổ biến là thiếu RAM hoặc local-path PVC chưa bind được.

## Mở Grafana

Terminal A mở Kubernetes API qua IAP:

```bash
make gcp-k3s-tunnel
```

Terminal B mở Grafana chỉ trên laptop:

```bash
make gcp-observability-grafana-port-forward
```

Mở `http://127.0.0.1:3000`. Lấy thông tin đăng nhập tại terminal khi cần, không
commit Secret hay gửi password vào chat/ticket:

```bash
ssh kuberag-gcp 'sudo k3s kubectl -n observability get secret kuberag-grafana-admin -o jsonpath="{.data.admin-user}" | base64 -d; echo'
ssh kuberag-gcp 'sudo k3s kubectl -n observability get secret kuberag-grafana-admin -o jsonpath="{.data.admin-password}" | base64 -d; echo'
```

Dashboard `KubeRAG Overview` có API request rate, p95 latency, status code gồm
`429`, RAG stage duration, memory và restart count. Grafana Explore dùng Loki,
Tempo hoặc Pyroscope khi cần điều tra từng request.

## Kiểm tra read-only

```bash
make gcp-observability-status

# Targets của Prometheus; `1` nghĩa target scrape được.
kubectl -n observability port-forward service/kuberag-monitoring-kube-prometheus 19090:9090
# Terminal khác:
curl --silent 'http://127.0.0.1:19090/api/v1/query?query=up%7Bjob%3D%22kuberag-rag-api%22%7D' | jq

# Metrics API không gọi LLM; chỉ đọc counter/histogram trong process.
kubectl -n rag port-forward service/kuberag-rag-api 18000:80
curl --silent http://127.0.0.1:18000/metrics | grep '^kuberag_'
```

Để theo một truy vấn thật, gửi request qua browser/API, giữ `trace_id` từ
response, rồi tìm chính giá trị đó trong Loki. Log JSON đã giới hạn field ở
`service`, event, request/trace ID, method, route, status và duration; không
đưa raw prompt, full document, Secret hay stack trace ra ngoài.

```text
response.trace_id -> Loki `{service_name="kuberag-rag-api"}` -> Tempo trace
                 -> spans: http.request, embed_query, pgvector_search,
                    build_prompt, llm_generate
```

Trong Pyroscope, chọn service `kuberag-rag-api` và CPU profile để xem flame
graph. Profile là thống kê CPU theo thời gian; nó không phải log request và
không chứa câu hỏi/đoạn văn người dùng.

## Lỗi thường gặp

| Triệu chứng | Kiểm tra | Ý nghĩa/cách xử lý |
|---|---|---|
| `kubectl` timeout | Tunnel Terminal A còn chạy? | Chạy lại `make gcp-k3s-tunnel`; không cần tạo cluster mới. |
| Grafana không mở | Port-forward còn chạy? | Mở lại port-forward, dùng `127.0.0.1:3000`, không dùng IP VM. |
| Không có log mới | `kubectl -n observability logs deploy/kuberag-otel-collector` | Kiểm tra Collector và Loki Running; ứng dụng phải có request mới. |
| Không thấy trace | Kiểm tra API `OTEL_ENABLED=true` và Tempo datasource | So khớp `trace_id` từ response, không đoán theo thời gian. |
| Pyroscope rỗng | Tạo workload có CPU rồi chờ ít nhất một upload interval | Pyroscope lấy mẫu định kỳ, không có flame graph ngay lập tức sau startup. |
| Disk/RAM cao | `kubectl top pods -n observability`, `kubectl get pvc -n observability` | Giảm retention trước khi tăng disk; không tăng limit mù quáng trên single-node. |

## Phần chưa hoàn tất

Alert rules/contact point, alert lifecycle test, k6 correlation và runtime
evidence screenshots vẫn là checkpoint tiếp theo. Không coi Pod `Running` là
bằng chứng một acceptance item đã Pass; cần query hoặc screenshot thực tế cho
từng tiêu chí `OBS-*`.
