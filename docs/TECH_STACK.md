# Tech stack và quyết định kỹ thuật

## 1. Nguyên tắc lựa chọn

- Đáp ứng đủ yêu cầu mentor trước khi tối ưu hình thức.
- Ưu tiên open source, nhẹ và chạy được CPU-only.
- Giảm số thành phần trùng chức năng.
- Ưu tiên công nghệ có Helm chart/operator và tài liệu Kubernetes tốt.
- Chỉ một công nghệ đảm nhiệm một trách nhiệm chính, trừ khi có lý do rõ ràng.
- Pin version khi triển khai; không ghi `latest` trong manifest hoặc CI.

## 2. Stack đã chốt

| Lớp | Công nghệ | Trạng thái | Vai trò | Lý do |
|---|---|---|---|---|
| Cloud | Local machine hoặc GCP Compute Engine | Required | Chạy single-node k3s tạm thời; khôi phục 3 VM ở mốc cuối | Chủ động cấu hình, dùng được Terraform/Ansible, kiểm soát chi phí |
| IaC | Terraform | Required | Single-node VM/local target tạm thời; VPC, firewall, VM, disk, IP ở mốc GCP | Tái lập hạ tầng và thể hiện IaC |
| Configuration | Ansible | Required | Cấu hình OS, cài k3s single-node; join worker ở mốc 3-node | Phù hợp quản lý node và mở rộng lại nhiều VM |
| Kubernetes | k3s | Required | Container orchestration | Nhẹ hơn kubeadm, vẫn là Kubernetes chuẩn |
| Package | Helm | Required | Cài platform/operator | Hệ sinh thái chart rộng |
| Overlay | Kustomize | Required | Custom app manifests | Native với kubectl, rõ khác biệt môi trường |
| Gateway | Envoy Gateway | Required | Gateway API, route, rate limit | Tách network policy khỏi service |
| Default ingress | Traefik | Disabled locally, unused | Thành phần k3s mặc định | Không phục vụ route của dự án |
| Frontend | React + Vite | Required | UI truy vấn một trang | Nhẹ, nhanh, đủ cho demo |
| Backend | FastAPI | Required | RAG HTTP API | Python, async, OpenAPI và dễ instrument |
| Orchestrator | Prefect | Required | Daily ingestion flow | Nhẹ và dễ tiếp cận hơn Airflow cho scope này |
| Sources | VnExpress RSS + NVD API | Required | Dữ liệu mới hằng ngày | Hai định dạng và domain khác nhau |
| Database | PostgreSQL | Required | OLTP, metadata, documents | Tin cậy, phù hợp dữ liệu quan hệ |
| DB operator | CloudNativePG | Required | Single PostgreSQL instance tạm thời; primary/replica/failover ở mốc cuối | Kubernetes-native PostgreSQL lifecycle |
| Vector | pgvector | Required | Embedding và similarity search | Tránh thêm vector database riêng |
| Migration | Alembic | Required | Version schema | Chuẩn Python và chạy lặp lại được |
| Embedding | `multilingual-e5-small` hoặc tương đương | Required | Vector hóa tiếng Việt/Anh | Nhỏ, multilingual, chạy CPU |
| LLM runtime | llama.cpp server | Required | Self-hosted inference | CPU-friendly, hỗ trợ GGUF quantized |
| LLM | `Qwen2.5-1.5B-Instruct` GGUF `Q4_K_M` | Required | Sinh câu trả lời demo | Baseline CPU-only đã chốt; phù hợp ngân sách tài nguyên của demo |
| Telemetry standard | OpenTelemetry | Required | Instrument logs/traces | Chuẩn mở, vendor-neutral |
| OTLP gateway | OpenTelemetry Collector | Required | Nhận/chuyển logs và traces | Một telemetry gateway chính |
| Metrics | Prometheus | Required | Scrape/lưu metrics | Chuẩn Kubernetes, PromQL/Grafana tốt |
| Logs | Loki | Required | Lưu/truy vấn logs | Nhẹ hơn full-text search stack cho demo |
| Traces | Tempo | Required | Lưu traces | Tích hợp Grafana/OTLP tốt |
| Profiles | Pyroscope + Python SDK | Required | Continuous profiling | Chứng minh profile không cần privileged agent |
| Dashboard | Grafana | Required | Dashboard/Explore/correlation | Một giao diện cho bốn signal |
| Alerting | Grafana Alerting + Telegram | Required | Rule, contact point, notification | Dễ provision và demo trực quan |
| Load test | k6 | Required | Load/stress/rate-limit tests | Scriptable, phù hợp CI và Prometheus dashboard |
| Base image | Chainguard | Required | Secure runtime base | Đáp ứng loại image mentor cho phép |
| SAST | Semgrep | Required | Scan source code | Rule-based, dễ chạy CI |
| Vulnerability/IaC | Trivy | Required | Scan fs/config/secret/image, SBOM | Một công cụ bao phủ nhiều yêu cầu |
| SBOM | Trivy SPDX/CycloneDX | Required | Danh sách thành phần | Tránh thêm tool nếu Trivy đáp ứng |
| Signing | Cosign | Required | Sign/verify image digest | Chuẩn phổ biến của Sigstore |
| CI | GitHub Actions | Required | Test, scan, build, sign | Repo đang sử dụng, dễ tích hợp GHCR/GCP |
| Registry | GHCR hoặc Artifact Registry | Required, chọn một | Lưu custom images | Chốt một registry ở tuần 1 để tránh song song |

## 3. Quyết định quan trọng

### 3.1. Compute Engine thay vì GKE

GKE là Kubernetes phù hợp nhưng không được chọn cho implementation chính vì:

- Dự án cần thể hiện Terraform và Ansible rõ ràng.
- Single-node k3s là mốc tạm thời để phù hợp máy local và giảm chi phí trong giai đoạn phát triển.
- k3s 3 node vẫn là quyết định kiến trúc cuối cần khôi phục trước final acceptance.
- Compute Engine cho phép học node, control plane và join cluster khi quay lại topology cuối.
- Chi phí/control dễ dự đoán hơn cho lab nhỏ.

GKE chỉ là phương án thay thế nếu mentor yêu cầu managed Kubernetes.

### 3.2. Prefect thay vì Dagster/Airflow

- Airflow mạnh nhưng nặng và nhiều thành phần cho scope nhỏ.
- Dagster có developer experience tốt nhưng thêm khái niệm asset/resource.
- Prefect đủ schedule, retry, timeout và monitoring với chi phí học/tài nguyên thấp hơn.

### 3.3. PostgreSQL/pgvector thay vì vector database riêng

- Dữ liệu gồm document, metadata, ingestion status và vector.
- PostgreSQL đáp ứng OLTP và quan hệ; pgvector bổ sung retrieval.
- Một data platform đơn giản hơn vận hành PostgreSQL cộng thêm Qdrant/Milvus.

### 3.4. CloudNativePG thay vì tự quản lý StatefulSet

Tự viết StatefulSet không tự giải quyết promotion, service role, reconciliation và lifecycle an toàn. CloudNativePG cung cấp operator và CRD phù hợp để chạy single instance tạm thời và chứng minh primary/replica/failover khi quay lại topology 3-node.

### 3.5. llama.cpp thay vì external LLM API

- Đáp ứng yêu cầu self-hosted.
- Chạy GGUF quantized trên CPU.
- OpenAI-compatible HTTP server giúp client đơn giản.
- Chất lượng model không phải mục tiêu đánh giá.

### 3.6. Model baseline và giới hạn nâng cấp

- Model generation mặc định là `Qwen2.5-1.5B-Instruct` ở định dạng GGUF,
  quantization `Q4_K_M`, chạy bằng một replica `llama.cpp` trên CPU.
- `Qwen3-1.7B` GGUF Q4 là ứng viên benchmark, không phải model triển khai
  mặc định. Chỉ đổi sau khi đo cùng bộ câu hỏi RAG, gồm latency, RAM tối đa,
  tốc độ sinh, OOM/restart và chất lượng nguồn trả về.
- Ở topology cuối, model nằm trên một worker duy nhất. Kubernetes không cộng
  CPU/RAM của nhiều worker để chạy một process `llama.cpp`; vì vậy model phải
  vừa tài nguyên của chính node chứa Pod đó.
- Không dùng model 3B hoặc lớn hơn làm baseline trên worker 2 vCPU / 8 GiB.
  Nếu cần nâng chất lượng, nâng riêng worker chứa LLM lên tối thiểu 4 vCPU /
  16 GiB, sau đó benchmark lại trước khi đổi model.
- Embedding vẫn dùng `multilingual-e5-small` hoặc tương đương cho đến khi
  implementation pin model, tokenizer, vector dimension và migration index.

### 3.7. OTel Collector không dùng Alloy

- OTel Collector là gateway chính cho OTLP logs/traces.
- Prometheus tự scrape metrics.
- Pyroscope SDK gửi profile trực tiếp.
- Alloy sẽ trùng vai trò và tăng CPU/RAM nếu chỉ thêm để “đủ stack”.

### 3.8. Envoy Gateway thay vì Traefik cho ứng dụng

Traefik vẫn có thể tồn tại trong k3s, nhưng toàn bộ route KubeRAG dùng Envoy Gateway. Rate limit nằm ở Gateway policy, đúng yêu cầu không thực hiện trong service.

### 3.9. LangGraph Agent không thuộc required scope

Source base hiện tại là Agent template, nhưng KubeRAG cần luồng deterministic:

```text
embed query → retrieve chunks → build bounded prompt → generate answer
```

LangGraph/tool-calling/in-memory agent checkpoint phải được loại bỏ hoặc cô lập khỏi release chính để giảm dependency và latency.

## 4. Công nghệ không được tự ý thêm

| Công nghệ | Chỉ thêm khi |
|---|---|
| Redis | Có nhu cầu cache/checkpoint/rate-limit đã đo và được phê duyệt |
| Kafka | Có yêu cầu event streaming rõ ràng |
| MinIO | Có yêu cầu object storage/backup không thể dùng phương án đơn giản hơn |
| Elasticsearch/OpenSearch | Loki/PostgreSQL không đáp ứng use case đã chứng minh |
| Grafana Alloy | OTel Collector/Prometheus không đáp ứng luồng telemetry cụ thể |
| Service mesh | Có yêu cầu mTLS/traffic policy vượt quá Gateway |
| Argo CD | Required scope đã hoàn thành và GitOps là optional được chọn |
| Vault | Secret lifecycle thực sự cần; Kubernetes/GitHub/GCP secrets không đủ |
| LangChain/LangGraph | Có lợi ích đo được; direct client không đáp ứng |

## 5. Version và dependency policy

- Local foundation pins validated on 2026-07-24: k3s `v1.35.5+k3s1`, Helm `v4.2.2`, and Envoy Gateway chart `v1.8.3`.
- Pin Terraform provider, Helm chart và application dependency trong file lock/config.
- Container image dùng version hoặc digest; production-like overlay dùng digest.
- Không dùng floating tag `latest`.
- Chỉ update dependency trong PR riêng nếu thay đổi lớn.
- `uv.lock` và frontend lockfile phải được commit.
- CI scan dependency/image sau mỗi build.
- Ghi version đã demo trong final release notes.

## 6. Required và optional rõ ràng

### Required

Toàn bộ dòng đánh dấu Required trong bảng stack phải có deployment, test và evidence.

### Optional

- TLS/public DNS hoàn chỉnh.
- Backup/restore nâng cao.
- Replica PostgreSQL thứ ba.
- SSE streaming.
- Signature admission enforcement.
- Autoscaling/GitOps.

Không được thêm optional trước feature freeze nếu required scope còn acceptance item chưa pass.
