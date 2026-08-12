# Limitations, resource usage, and cost posture

Last reviewed: 2026-08-12.

## Runtime scope

KubeRAG đang là proof of concept production-like, không phải dịch vụ có SLA.
Topology đang chạy là một k3s server và hai worker private trên GCP:

| Node | Vai trò chính | CPU cấu hình | Memory cấu hình |
| --- | --- | ---: | ---: |
| `kuberag-server` | control plane, Prefect Server, Envoy entry | 8 vCPU | 16 GiB |
| `kuberag-worker-application` | API, web, llama.cpp, Prefect worker, PG replica | 4 vCPU | 16 GiB |
| `kuberag-worker-observability` | Prometheus/Grafana/Loki/Tempo/Pyroscope, PG primary | 2 vCPU | 8 GiB |

Storage dùng `pd-balanced`: server có boot disk 30 GiB + data disk 150 GiB;
mỗi worker có boot disk 30 GiB + data disk 50 GiB. Local-path PVC là
node-local, nên không thể di chuyển stateful Pod chỉ bằng đổi node selector.

Prometheus snapshot ngày 2026-08-12 ghi nhận workload usage thấp: application
worker ~22% RAM, observability worker ~17% RAM, server ~4% RAM; CPU tương ứng
~2.1%, ~4.7% và ~0.5%. Đây là container workload/capacity, không bao gồm host
OS; xem evidence `OBS-003/gcp-node-workload-utilization-2026-08-12.md`.

## Hiệu năng và giới hạn đã biết

- Luồng chính là CPU-only: `embed -> pgvector retrieve -> bounded prompt ->
  llama.cpp generate`; generation là nút thắt, không phải retrieval.
- API/UI mặc định `top_k=3`. Caller chỉ nên dùng `top_k=5` khi chấp nhận context
  và thời gian generation lớn hơn.
- Kết quả tải đã chứng minh safe bound là tối đa 3 virtual users, think time 35
  giây: 9/9 request thành công, p95 2.458 giây. Đây không phải throughput hoặc
  capacity production.
- Envoy áp rate limit 10 request/phút; `429` là cơ chế bảo vệ có chủ đích.
- Warm-up sidecar giữ API ngoài traffic đến khi một request loopback ngắn thành
  công, giảm cold-start nhưng không biến inference CPU thành realtime.

## Security and access posture

- Envoy `:8080` bị giới hạn bằng firewall allow-list của operator; không dùng
  DuckDNS/domain public trong đường vận hành hiện tại.
- Demo API đang ở `PUBLIC_DEMO_MODE`, không yêu cầu bearer token. Điều này chỉ
  chấp nhận được khi allow-list rất hẹp; mở firewall rộng hoặc share URL công
  khai sẽ làm bất kỳ người dùng nào có thể tiêu thụ model quota và đọc câu trả
  lời/nguồn. Khi mở rộng phạm vi, phải bật authentication và TLS trước.
- Observability là `ClusterIP` và chỉ truy cập qua IAP + localhost port-forward.
- Lần evidence supply-chain đầy đủ gần nhất là 2026-08-03. Trivy mới không chạy
  trong lần rà soát này theo chỉ đạo operator; vì vậy không được gắn release tag
  mới như thể đã có image scan/SBOM/Cosign mới.
- `SEC-009` branch protection vẫn chờ quyền GitHub repository administrator để
  có evidence ruleset/required CI checks.

## Cost control

Ngân sách cảnh báo hiện tại là VND 3,000,000/tháng. Budget alert chỉ gửi cảnh
báo, **không** chặn chi tiêu. VM đang chạy vẫn phát sinh compute; kể cả khi
stop, disk, reserved external IP và Artifact Registry vẫn có thể phát sinh
phí. Vì pricing tuỳ billing account/discount và dữ liệu Billing có độ trễ, tài
liệu không suy đoán một con số chi phí thực tế.

Mỗi tuần cần đối chiếu Cloud Billing export/console theo project
`kube-rag-platform`, sau đó dừng ba VM ngoài giờ khi không demo. Runbook an
toàn tại [`runbooks/gcp-cost-control.md`](runbooks/gcp-cost-control.md) mô tả
stop/start/destroy và tác động của từng bước.

## Deferred release gates

`DOC-006` (demo script/rehearsal) được operator chủ động hoãn. Do `DOC-006` là
Required, `DOC-007` không thể đánh dấu tất cả Required Pass và `DOC-008` không
được tạo release tag cuối cùng cho tới khi rehearsal hoàn tất. Đây là gate tài
liệu/release, không phải lỗi runtime của cluster.
