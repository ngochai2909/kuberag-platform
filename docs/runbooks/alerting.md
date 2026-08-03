# Alerting on the single-node demo

## Mục tiêu

Prometheus đánh giá `PrometheusRule`; Alertmanager nhóm alert rồi gửi Slack khi
điều kiện duy trì đủ lâu. Grafana vẫn là nơi xem dashboard và trạng thái alert.

```text
PrometheusRule -> Prometheus evaluation -> Alertmanager -> Slack incoming webhook
```

`observability/alerts/kuberag-rules.yaml` chứa rule thường trực. Chart values
`deploy/helm/observability/kube-prometheus-stack-values.yaml` bật đúng một
Alertmanager nhỏ (96 MiB request, 192 MiB limit). Cấu hình route không nhạy cảm
ở `observability/alertmanager/config-secret.yaml`; URL webhook chỉ nằm trong
Kubernetes Secret `kuberag-slack-webhook`, được mount và đọc bằng
`api_url_file`. Do đó URL không xuất hiện trong Git, Helm values, log hoặc
evidence.

## Checkpoint 1: render local

Lệnh này chỉ render template ra stdout; không kết nối Kubernetes, không tạo
Secret và không gửi Slack:

```bash
make gcp-observability-render
kubectl kustomize observability
```

Kiểm tra render có `PrometheusRule/kuberag-platform-alerts`,
`Secret/kuberag-alertmanager-config` và `Alertmanager`. Envoy được scrape qua
`observability/servicemonitors/envoy-gateway.yaml`, cổng metrics `19001` và
`/stats/prometheus`, đã được phát hiện từ data plane đang chạy thay vì đoán.

## Checkpoint 2: tạo webhook Secret và cài/upgrade Alertmanager

Đây là thay đổi cluster (tạo/đổi một Secret và Helm workloads), nhưng không tạo
VM, firewall hay public port. Cần xác nhận riêng ngay trước khi chạy. Trong
shell hiện tại, đặt biến môi trường cục bộ; không paste URL vào chat, Git hay
history:

```bash
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/REDACTED'
make gcp-alertmanager-slack-secret
make gcp-observability-install
make gcp-observability-apply
```

Script chỉ tạo/upsert `kuberag-slack-webhook` bằng `kubectl create secret
--dry-run=client | kubectl apply`; nó không in URL. `resolve_timeout: 1m`,
`group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 4h` và
`send_resolved: true` nằm trong config Secret không nhạy cảm.

Sau đó chạy kiểm tra chỉ-đọc:

```bash
make gcp-observability-status
kubectl -n observability get alertmanager,prometheusrule
```

`Running` không chứng minh Slack nhận alert; cần checkpoint sau.

## Checkpoint 3: chứng minh lifecycle

`observability/alerts/test-lifecycle.yaml` là rule tách riêng, `vector(1)` với
`for: 30s`. Nó không gọi API, Prefect hay PostgreSQL. Việc apply/delete thay đổi
cluster và gửi Slack, nên cần xác nhận riêng. Sau khi Slack nhận `Firing`, chạy
lệnh cleanup và chờ `Resolved`:

```bash
make gcp-alert-lifecycle-test
# chờ ít nhất 30 giây + một chu kỳ Prometheus rồi lưu timestamp/screenshot
make gcp-alert-lifecycle-cleanup
```

Lưu timestamp/ảnh Slack đã che tên workspace và URL ở
`docs/evidence/ALT-008/`. Không copy JSON Secret hay output chứa URL webhook.

## Các rule và phản ứng đầu tiên

| Alert | Ý nghĩa | Kiểm tra chỉ-đọc đầu tiên |
| --- | --- | --- |
| `KubeRagApiHigh5xxRate` | Có ít nhất 5 request và trên 5% là 5xx trong 5 phút | Grafana API codes, logs theo `trace_id`, API Pod restart |
| `KubeRagApiHighP95Latency` | p95 API >45 giây trong 5 phút | RAG stage duration, llama.cpp CPU/RAM |
| `KubeRagWorkloadHighMemory` | API/worker >85% memory limit | `kubectl top pods -n rag,prefect`; không tăng limit mù quáng |
| `KubeRagWorkloadRestarted` | API hoặc worker restart trong 15 phút | `kubectl logs --previous`, events |
| `KubeRagIngestionFailed` | Timestamp failure ingestion trong 30 phút | Prefect run/log, không rerun mù quáng vì có thể upsert |
| `KubeRagPostgresNotReady` | PostgreSQL không Ready quá 2 phút | CNPG Cluster/Pod/PVC; không xóa Pod/PVC để sửa |
| `KubeRagEnvoyRateLimitSpike` | Ít nhất 5 response `429` trong 5 phút | Envoy status/rate-limit metrics, k6 rate-limit report |

PostgreSQL single-node không có replica để failover; đây là cảnh báo
unavailable, không phải bằng chứng HA hay backup.

## Failure test RSS/Prefect có kiểm soát

`make gcp-release-ingestion-failure-test` là Job test-only, cố ý gọi flow
Prefect với `http://127.0.0.1:1` bên trong **chính Pod Job**. Địa chỉ đó không
phải VnExpress, không ra Internet và không ghi tài liệu/chunk/embedding: lỗi
xảy ra trước bước upsert. Flow vẫn gửi log, trace, counter
`kuberag_ingestion_runs_total{status="failed"}` và gauge
`kuberag_ingestion_last_failure_timestamp_seconds` qua OTel Collector. Rule
`KubeRagIngestionFailed` so sánh gauge này với thời điểm hiện tại, nên Firing
ngay cả khi process ngắn hạn chỉ export counter lần đầu ở giá trị `1`.

Lệnh này tạo một Job `Failed`, một Prefect flow run `Failed` và một Slack alert;
nó thay đổi cluster nhưng không tạo VM/disk/firewall. Chỉ chạy sau khi image
release chứa manifest đã được review, có xác nhận riêng, và operator sẵn sàng
chụp evidence. Không dùng trong lúc daily schedule đang được debug.

Sau `Firing`, chỉ đọc trạng thái/log/Prometheus, lưu evidence rồi chờ cửa sổ
30 phút của rule trôi qua để nhận `Resolved`. Job có TTL 24 giờ; không xóa
`ingestion_runs` hay sửa metric để ép alert biến mất.
