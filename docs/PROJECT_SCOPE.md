# Phạm vi dự án KubeRAG

## 1. Thông tin dự án

- **Tên ngắn:** KubeRAG
- **Tên đầy đủ:** KubeRAG — A Secure and Observable Cloud-Native RAG Platform on Kubernetes
- **Loại dự án:** Cloud-Native Platform Engineering / DevOps Capstone
- **Thời lượng mục tiêu:** 6 tuần, một intern, full-time
- **Môi trường chính tạm thời:** single-node k3s để phát triển local và demo ràng buộc tài nguyên
- **Mục tiêu cuối:** Google Cloud Compute Engine, cụm k3s gồm 1 server và 2 worker
- **Kết quả:** production-like proof of concept, không cam kết production thực tế

## 2. Bài toán

Xây dựng một nền tảng có khả năng:

1. Thu thập dữ liệu mới hằng ngày từ hai nguồn độc lập.
2. Chuẩn hóa, chống trùng, chia đoạn, tạo embedding và lưu dữ liệu.
3. Truy xuất các đoạn liên quan bằng vector search.
4. Sinh câu trả lời qua LLM self-hosted và trả kèm nguồn.
5. Chạy toàn bộ workload trên Kubernetes với Pod Security `restricted`.
6. Quan sát được metrics, logs, traces và profiles.
7. Có dashboard, alert, stress test và rate limit tại gateway.
8. Có kiểm tra source/image, SBOM và chữ ký container image.
9. Có thể dựng lại bằng code và tài liệu, hạn chế thao tác thủ công.

Chất lượng nội dung do LLM sinh ra **không phải tiêu chí đánh giá chính**. Trọng tâm là khả năng triển khai, vận hành, quan sát, kiểm thử và bảo vệ nền tảng.

## 3. Mục tiêu

### 3.1. Mục tiêu kỹ thuật

- Tạo single-node k3s tạm thời bằng Terraform/Ansible hoặc local automation phù hợp.
- Giữ thiết kế có đường quay lại cụm k3s 3 node trên GCP bằng Terraform và Ansible.
- Dùng Envoy Gateway làm entry point duy nhất cho frontend và RAG API.
- Lưu dữ liệu trong PostgreSQL/pgvector. Mốc tạm thời dùng 1 instance; mốc cuối khôi phục 1 primary và ít nhất 1 replica.
- Điều phối ingestion bằng Prefect với schedule, retry, timeout và idempotency.
- Chạy FastAPI RAG API, React/Vite UI và llama.cpp self-hosted.
- Dùng Prometheus, Loki, Tempo, Pyroscope và Grafana cho observability.
- Gửi alert qua Telegram.
- Chứng minh RPS, latency, CPU, RAM, error rate và `429` trong k6 test.
- Bảo vệ software supply chain bằng Chainguard, Semgrep, Trivy, SBOM và Cosign.

### 3.2. Mục tiêu học tập

- Hiểu quan hệ giữa container, Pod, node, Service và Gateway.
- Biết dùng Infrastructure as Code và configuration management.
- Biết vận hành stateful workload và kiểm thử failover.
- Biết instrument, thu thập và correlate telemetry.
- Biết xây CI có test, scan, build, sign và verify.
- Có khả năng giải thích trade-off của từng quyết định trong buổi demo.

## 4. Người dùng và stakeholder

| Đối tượng | Nhu cầu |
|---|---|
| Người dùng demo | Nhập câu hỏi và nhận câu trả lời kèm nguồn |
| Người vận hành | Xem dashboard, trace, log, profile và alert |
| Người phát triển | Chạy test, build image và deploy bằng lệnh tái lập |
| Mentor/reviewer | Kiểm chứng đầy đủ yêu cầu bằng bằng chứng rõ ràng |

## 5. Phạm vi bắt buộc

### 5.1. Hạ tầng và Kubernetes

- Single-node k3s là phạm vi bắt buộc tạm thời để phát triển trên máy local hoặc một VM.
- Cụm cuối quay lại 1 server/control plane và 2 worker trên GCP Compute Engine trong cùng VPC và một zone.
- Terraform tạo network, firewall, VM, disk và output cần thiết.
- Ansible cài và cấu hình k3s server single-node; logic join worker được hoãn tới mốc 3-node.
- Helm cài các nền tảng bên thứ ba; Kustomize quản lý workload của dự án.
- Namespace và custom workload tuân thủ PSS `restricted`.
- Traefik có thể tồn tại do k3s cài mặc định nhưng không phục vụ route dự án.

### 5.2. Data ingestion

- Hai nguồn dữ liệu: VnExpress RSS và NVD CVE API.
- Có fixture/sample data để test offline và dự phòng khi nguồn lỗi.
- Prefect flow hằng ngày: `fetch → normalize → deduplicate → chunk → embed → upsert`.
- Có retry, timeout, exponential backoff, watermark và trạng thái ingestion run.
- Chạy lại cùng input không tạo document/chunk trùng.

### 5.3. Data storage

- CloudNativePG quản lý PostgreSQL cluster.
- Mốc tạm thời dùng 1 PostgreSQL instance có persistent volume.
- Mốc cuối dùng tối thiểu 2 instance: 1 primary và 1 replica.
- Mỗi instance có persistent volume.
- Bật extension `vector` và sử dụng pgvector.
- Có schema migration, constraint chống trùng và vector index phù hợp.
- Có kiểm thử persistence và restart ở mốc tạm thời.
- Kiểm thử replication và switchover/failover được hoãn tới mốc 3-node.

### 5.4. RAG và ứng dụng

- FastAPI cung cấp API truy vấn RAG và health endpoints.
- React/Vite cung cấp UI một trang, responsive, đơn giản.
- Embedding model nhỏ chạy CPU, ưu tiên model multilingual.
- llama.cpp chạy LLM GGUF quantized, CPU-only, 1 replica.
- Luồng demo chính không gọi external LLM API.
- Câu trả lời có danh sách nguồn, request ID, trace ID và latency.
- Envoy Gateway route `/` tới frontend và `/api/` tới FastAPI.
- Rate limit được cấu hình bằng policy của Envoy Gateway, không nằm trong FastAPI.

### 5.5. Observability và alerting

- Prometheus scrape infrastructure, Kubernetes, Envoy và application metrics.
- FastAPI và ingestion gửi OTLP logs/traces tới OpenTelemetry Collector.
- OpenTelemetry Collector là telemetry gateway chính cho OTLP logs/traces.
- Loki lưu logs; Tempo lưu traces.
- Pyroscope Python SDK gửi profiles trực tiếp tới Pyroscope.
- Grafana provision data sources, dashboard và alert rules từ Git.
- Dashboard hiển thị RPS, percentiles latency, status codes, `429`, CPU, RAM, restart, ingestion và PostgreSQL health.
- Telegram nhận ít nhất một alert được kích hoạt bởi workload/test thật.
- Không cài Grafana Alloy nếu không xuất hiện yêu cầu kỹ thuật mới được phê duyệt.

### 5.6. Performance và security

- k6 có load test và rate-limit test.
- Có threshold cho latency và error rate.
- Custom image sử dụng Chainguard làm base image.
- Source và manifest pass Semgrep/Trivy theo policy của dự án.
- Mỗi custom image có SBOM, được Cosign sign theo digest và verify thành công.
- Final deployment tham chiếu immutable image digest.
- CI không chứa secret thật và không ghi raw prompt/document nhạy cảm vào log.

### 5.7. Tài liệu và release

- Có kiến trúc, hướng dẫn cài đặt, runbook, acceptance checklist và demo script.
- Có lệnh tự động hóa cho deploy, status, smoke test, load test và destroy.
- Có clean-install test từ một môi trường mới hoặc đã dọn sạch.
- Có release tag và evidence cho toàn bộ yêu cầu bắt buộc.

### 5.8. Phạm vi hoãn tới mốc 3-node

Các mục này không chặn mốc single-node tạm thời, nhưng phải được khôi phục trước khi quay lại đúng yêu cầu cuối:

- Cụm k3s 1 server và 2 worker trên GCP.
- PostgreSQL primary/replica tách node.
- Replication lag, switchover/failover và node placement evidence.

## 6. Phạm vi optional

Chỉ thực hiện sau khi toàn bộ required scope đã pass. Chọn tối đa một hoặc hai mục có giá trị cao:

- PostgreSQL replica thứ ba.
- SSE streaming cho câu trả lời.
- TLS với chứng chỉ tin cậy.
- Backup/restore PostgreSQL có kiểm thử.
- Admission policy xác minh Cosign signature trước khi deploy.
- Autoscaling cho stateless workloads.
- Grafana correlation nâng cao hoặc exemplar.
- Terraform remote state và CI deploy bán tự động.

Optional phải nằm trên branch/PR riêng và có thể loại khỏi release mà không ảnh hưởng required scope.

## 7. Ngoài phạm vi

- Huấn luyện hoặc fine-tune LLM.
- Đánh giá chất lượng model chuyên sâu.
- Multi-agent hoặc tool-calling agent orchestration.
- Authentication đa người dùng, RBAC cấp ứng dụng hoặc billing.
- Mobile app.
- Kafka, Redis, MinIO, Elasticsearch hoặc service mesh nếu không có nhu cầu đã chứng minh.
- Kubernetes control-plane HA; cụm chỉ có một k3s server.
- Multi-region hoặc multi-zone disaster recovery.
- Production SLA/SLO chính thức.
- Tự động scale LLM hoặc GPU inference.

## 8. Ràng buộc

- Ngân sách GCP tối đa 300 USD; phải có budget alert và tắt VM khi không cần.
- Free-trial không dùng GPU; workload AI phải chạy CPU-only.
- Resource mốc tạm thời phải phù hợp máy single-node 16 GiB RAM bằng cách dùng model nhỏ, retention ngắn và không chạy workload nặng song song.
- Resource mốc cuối phải phù hợp cấu hình 1 server 4 GiB và 2 worker 8 GiB, trừ khi nâng tạm thời có phê duyệt.
- Không commit credential, token, private key, kubeconfig hoặc Terraform state chứa dữ liệu nhạy cảm.
- Không thay đổi stack đã chốt nếu chưa cập nhật tài liệu và ghi lý do.
- Một intern phải có khả năng clean install và demo hệ thống.

## 9. Giả định

- GCP project, billing, quota và quyền tạo VM đã sẵn sàng.
- Các nguồn VnExpress/NVD cho phép truy cập trong phạm vi demo; fixture là phương án dự phòng.
- Chất lượng câu trả lời không được chấm; model nhỏ là đủ.
- Tải mục tiêu dùng để quan sát hành vi, không nhằm chứng minh quy mô production.
- Telegram là kênh alert chính.

## 10. Deliverables

- Repository `kuberag-platform` với source, IaC, manifest, test và docs.
- Ba custom image: `kuberag-api`, `kuberag-web`, `kuberag-ingestion`.
- Terraform/Ansible dựng được hạ tầng và k3s.
- Helm/Kustomize triển khai được platform và applications.
- PostgreSQL/pgvector single-instance tạm thời và dữ liệu hai nguồn; primary-replica được khôi phục ở mốc 3-node.
- RAG API, frontend và self-hosted LLM hoạt động end-to-end.
- Grafana dashboard, Telegram alert và k6 report.
- Semgrep/Trivy reports, SBOM và Cosign verification output.
- Runbooks, evidence, demo script và final release tag.

## 11. Tiêu chí thành công cấp cao

Dự án thành công khi một reviewer có thể dùng repository và tài liệu để:

1. Dựng cluster và deploy hệ thống.
2. Chạy ingestion hoặc nạp fixture.
3. Hỏi câu hỏi trên UI và nhận câu trả lời có nguồn.
4. Tìm request tương ứng trong metrics, logs, traces và profiles.
5. Chạy k6, quan sát RPS/latency/CPU/RAM và nhận alert.
6. Chứng minh rate limit trả `429` ở Gateway.
7. Chứng minh PostgreSQL persistence/restart ở mốc tạm thời; replication/failover ở mốc 3-node.
8. Chứng minh source/image đã scan, image có SBOM và chữ ký hợp lệ.

