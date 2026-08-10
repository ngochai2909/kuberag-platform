# Báo cáo tiến độ – KubeRAG Platform

**Demo deploy:** [http://136.85.35.106:8080](http://136.85.35.106:8080)  
- Tin: [http://136.85.35.106:8080/](http://136.85.35.106:8080/)  
- Chat: [http://136.85.35.106:8080/chat](http://136.85.35.106:8080/chat)  
- API status: [http://136.85.35.106:8080/api/v1/status](http://136.85.35.106:8080/api/v1/status)

## 1. Đã làm

### Kiến trúc và luồng hệ thống

- Nắm kiến trúc tổng thể: React, FastAPI RAG API, PostgreSQL/pgvector, E5, llama.cpp, Prefect, k3s, observability.
- Luồng end-to-end:

```text
VnExpress RSS → Prefect (chunk/embed/upsert) → PostgreSQL/pgvector
       → FastAPI (retrieve + prompt) → llama.cpp → React (Tin / Chat)
```

### Ingestion và RAG

- Pipeline VnExpress RSS: fetch → normalize → chunk → E5 embedding → upsert idempotent.
- Prefect quản lý flow/schedule.
- RAG API: embed query → pgvector → prompt → llama.cpp → answer + sources (kèm timing/debug fields).

### Frontend

- Trang Tin (duyệt bài theo chuyên mục) và Chat (hỏi đáp RAG + nguồn).
- Kết nối API thật; xử lý lỗi cơ bản (rate limit, auth/API).

### Hạ tầng

- Triển khai k3s 3 node trên gcp (server + application worker + observability worker).
- Terraform / Ansible / Helm / Kustomize cho provision, cấu hình và workload.
- Envoy Gateway làm entrypoint demo.

### CI/CD và security (cơ bản)

- GitHub Actions: lint, typecheck, test, frontend build.
- Semgrep/Trivy, build image, SBOM, ký digest; OIDC với GCP (không lưu SA key dài hạn).

## 2. Đang làm

### Observability

- Đang triển khai/hoàn thiện stack: Prometheus, Grafana, Loki, Tempo, Pyroscope, OTel Collector.
- Mục tiêu: theo dõi request RAG theo `trace_id` / `request_id`, dashboard latency/error, alert cơ bản.
- thiết lập Alert trên slack

## 3. Việc tiếp theo

- Chuẩn bị end-to-end (cluster → ingest → Tin → Chat → API → observability).
- Cải thiện chất lượng RAG (eval cố định, `top_k`, prompt); auth/rate-limit theo hướng production hơn khi cần.
- Kiểm tra backup/restore DB, resource limit, load test khi ổn định demo.

## 4. Khó khăn / lưu ý

- LLM self-hosted (llama.cpp, chủ yếu CPU) → latency generation còn cao; tài nguyên cluster dễ cạnh tranh.
- Một số cấu hình đang ưu tiên demo, chưa phải production cứng.
