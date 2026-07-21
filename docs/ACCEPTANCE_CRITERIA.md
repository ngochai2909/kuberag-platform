# Acceptance criteria KubeRAG

## 1. Cách sử dụng

Mỗi tiêu chí có trạng thái:

- `Not started`
- `In progress`
- `Pass`
- `Fail`
- `Blocked`
- `N/A` chỉ được dùng cho Optional

Một tiêu chí Required chỉ được đánh dấu `Pass` khi có cả:

1. Hành vi chạy thật đúng kỳ vọng.
2. Lệnh/test có kết quả thành công.
3. Evidence được lưu trong `docs/evidence/<criterion-id>/`.
4. Manifest/source liên quan đã commit.

Screenshot không thay thế manifest hoặc test output; manifest không thay thế runtime verification.

## 2. Infrastructure as Code

| ID      | Mức      | Tiêu chí                                                      | Cách kiểm chứng                                          | Evidence tối thiểu                        |
| ------- | -------- | ------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------- |
| INF-001 | Required | Terraform tạo VPC/subnet/firewall/3 VM/disks/IP đúng thiết kế | `terraform fmt -check`, `validate`, review `plan`, apply | plan summary, VM/network inventory        |
| INF-002 | Required | Chạy lại Terraform sau apply không có drift ngoài dự kiến     | `terraform plan -detailed-exitcode`                      | output no changes hoặc giải thích drift   |
| INF-003 | Required | Ansible cài k3s server và join 2 worker                       | chạy playbook từ môi trường mới                          | recap không fail, inventory               |
| INF-004 | Required | Ansible idempotent                                            | chạy playbook lần hai                                    | `changed=0` hoặc thay đổi được giải thích |
| INF-005 | Required | Có budget alert và hướng dẫn stop/start/destroy               | kiểm tra Billing và runbook                              | ảnh budget, runbook                       |
| INF-006 | Required | Secret/kubeconfig/state nhạy cảm không nằm trong Git          | Trivy secret + `git ls-files` review                     | scan report                               |

## 3. Kubernetes và Pod Security

| ID      | Mức      | Tiêu chí                                                              | Cách kiểm chứng                                      | Evidence tối thiểu             |
| ------- | -------- | --------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------ |
| K8S-001 | Required | 1 server và 2 worker ở trạng thái `Ready`                             | `kubectl get nodes -o wide`                          | output nodes                   |
| K8S-002 | Required | Node labels/placement phù hợp kiến trúc                               | `kubectl get nodes --show-labels`, list Pods by node | output/screenshot              |
| K8S-003 | Required | Namespace custom workload enforce/audit/warn `restricted`             | xem namespace labels                                 | YAML/output                    |
| K8S-004 | Required | Manifest an toàn chạy thành công                                      | apply safe manifest                                  | Pod Running và securityContext |
| K8S-005 | Required | Manifest privileged/root bị admission từ chối                         | apply unsafe manifest                                | thông báo rejection            |
| K8S-006 | Required | Custom workloads non-root, seccomp, drop ALL, no privilege escalation | render manifests + runtime inspect                   | Trivy config và Pod spec       |
| K8S-007 | Required | Custom workloads có requests/limits và probes                         | policy/script kiểm tra manifests                     | report                         |
| K8S-008 | Required | Không custom workload dùng privileged, hostPath hoặc host namespace   | manifest scan                                        | report                         |
| K8S-009 | Required | Pod restart không mất config/dữ liệu cần persistence                  | delete Pod có kiểm soát                              | trước/sau restart              |

## 4. Gateway và networking

| ID      | Mức      | Tiêu chí                                                  | Cách kiểm chứng                     | Evidence tối thiểu          |
| ------- | -------- | --------------------------------------------------------- | ----------------------------------- | --------------------------- |
| NET-001 | Required | Envoy GatewayClass/Gateway/HTTPRoute Accepted và resolved | `kubectl get ... -o yaml`           | conditions `True`           |
| NET-002 | Required | `/` route tới React frontend                              | HTTP request/browser                | response/screenshot         |
| NET-003 | Required | `/api/` route tới FastAPI                                 | curl qua public endpoint            | status/body/header          |
| NET-004 | Required | Traefik không phục vụ route KubeRAG                       | inspect Ingress/Routes/GatewayClass | resource list               |
| NET-005 | Required | Rate limit được cấu hình bằng Envoy policy                | inspect BackendTrafficPolicy        | manifest/status             |
| NET-006 | Required | Tải bình thường trả `200`, tải vượt limit có `429`        | k6 rate-limit scenario              | k6 summary và Envoy metrics |
| NET-007 | Required | FastAPI không có rate-limit middleware                    | source review/search/test           | review output               |
| NET-008 | Optional | Public HTTPS hợp lệ                                       | TLS handshake/browser               | certificate/output          |

## 5. PostgreSQL và pgvector

| ID     | Mức      | Tiêu chí                                                          | Cách kiểm chứng             | Evidence tối thiểu      |
| ------ | -------- | ----------------------------------------------------------------- | --------------------------- | ----------------------- |
| DB-001 | Required | CloudNativePG cluster có 1 primary và ít nhất 1 replica           | CNPG status/Pods            | status output           |
| DB-002 | Required | Primary và replica ở hai worker khác nhau                         | `kubectl get pods -o wide`  | node placement          |
| DB-003 | Required | Mỗi instance có PVC bound                                         | inspect PVC/PV              | output                  |
| DB-004 | Required | `vector` extension hoạt động                                      | SQL query extension/version | query output            |
| DB-005 | Required | Migration tạo documents/chunks/ingestion_runs và constraints      | chạy migration từ DB rỗng   | migration log/schema    |
| DB-006 | Required | Migration có thể chạy lại an toàn                                 | chạy upgrade lần hai        | successful/no-op output |
| DB-007 | Required | Insert/query vector hoạt động                                     | integration test            | test output             |
| DB-008 | Required | Replication healthy và lag quan sát được                          | CNPG/Prometheus query       | metric/status           |
| DB-009 | Required | Switchover/failover promote replica và service tiếp tục hoạt động | failure test có thời gian   | timeline, new primary   |
| DB-010 | Required | Dữ liệu còn sau Pod restart/failover                              | query trước/sau             | checksums/counts        |
| DB-011 | Optional | Backup và restore đã kiểm thử                                     | restore vào target sạch     | restore report          |

## 6. Data ingestion

| ID      | Mức      | Tiêu chí                                                      | Cách kiểm chứng                  | Evidence tối thiểu       |
| ------- | -------- | ------------------------------------------------------------- | -------------------------------- | ------------------------ |
| ING-001 | Required | Adapter VnExpress lấy/normalize dữ liệu thật hoặc fixture     | unit/integration test            | sample contract          |
| ING-002 | Required | Adapter NVD lấy/normalize dữ liệu thật hoặc fixture           | unit/integration test            | sample contract          |
| ING-003 | Required | Hai adapter trả cùng document contract                        | contract tests                   | test output              |
| ING-004 | Required | External calls có timeout/retry/backoff và user-agent phù hợp | tests mô phỏng timeout/429/5xx   | test output              |
| ING-005 | Required | Prefect flow có schedule hằng ngày                            | inspect deployment/schedule      | Prefect UI/config        |
| ING-006 | Required | Pipeline thực hiện fetch→normalize→dedup→chunk→embed→upsert   | flow run end-to-end              | Prefect run              |
| ING-007 | Required | Chạy lại cùng input không tăng document/chunk trùng           | chạy hai lần, so counts/checksum | SQL counts               |
| ING-008 | Required | `ingestion_runs` ghi success/failure/count/duration           | SQL query                        | records                  |
| ING-009 | Required | Chunk size/overlap có cấu hình và test boundary               | unit tests                       | test output              |
| ING-010 | Required | Embedding batch chạy trong resource limit                     | run sample batch                 | CPU/RAM/latency          |
| ING-011 | Required | Flow failure tạo metric/log/alert                             | inject failure                   | trace/log/alert evidence |

## 7. RAG API và self-hosted LLM

| ID      | Mức      | Tiêu chí                                                          | Cách kiểm chứng              | Evidence tối thiểu  |
| ------- | -------- | ----------------------------------------------------------------- | ---------------------------- | ------------------- |
| RAG-001 | Required | `POST /api/v1/query` validate request và trả schema đã định nghĩa | contract/integration tests   | OpenAPI + tests     |
| RAG-002 | Required | Query embedding và pgvector retrieval trả top-k chunks            | integration test fixture     | result/score        |
| RAG-003 | Required | Prompt builder giới hạn context và phân tách instruction/document | unit tests                   | test cases          |
| RAG-004 | Required | llama.cpp server chạy model GGUF quantized                        | health/model request         | endpoint/output     |
| RAG-005 | Required | Luồng demo chính không dùng external LLM API                      | config/network/source review | env/config evidence |
| RAG-006 | Required | Response có answer, sources, request ID, trace ID và latency      | API test                     | JSON response       |
| RAG-007 | Required | Timeout DB/embedding/LLM map thành lỗi công khai phù hợp          | failure tests                | status/error bodies |
| RAG-008 | Required | Không trả stack trace hoặc secret cho client                      | negative tests               | test output         |
| RAG-009 | Required | `/health/live`, `/health/ready`, `/metrics` đúng hành vi          | probe/HTTP tests             | output              |
| RAG-010 | Required | Model/API không vượt resource limit trong tải mục tiêu            | k6 + dashboard               | CPU/RAM/no OOM      |
| RAG-011 | Optional | SSE streaming hoạt động và client xử lý disconnect                | integration test             | recording/output    |

## 8. Frontend

| ID      | Mức      | Tiêu chí                                                     | Cách kiểm chứng    | Evidence tối thiểu |
| ------- | -------- | ------------------------------------------------------------ | ------------------ | ------------------ |
| WEB-001 | Required | UI gửi câu hỏi và hiển thị answer                            | browser test       | screenshot/video   |
| WEB-002 | Required | Source cards hiển thị title/URL/source                       | UI test            | screenshot         |
| WEB-003 | Required | Loading, empty và error state rõ ràng                        | component/e2e test | test/screenshots   |
| WEB-004 | Required | Hiển thị latency, request ID và trace ID                     | browser test       | screenshot         |
| WEB-005 | Required | Xử lý `429` thân thiện                                       | rate-limit UI test | screenshot         |
| WEB-006 | Required | Render nội dung an toàn, không thực thi HTML/script từ model | security test      | test output        |
| WEB-007 | Required | Frontend image dùng Chainguard và chạy PSS restricted        | image/Pod inspect  | scan/spec          |

## 9. Metrics, logs, traces và profiles

| ID      | Mức      | Tiêu chí                                                          | Cách kiểm chứng            | Evidence tối thiểu        |
| ------- | -------- | ----------------------------------------------------------------- | -------------------------- | ------------------------- |
| OBS-001 | Required | Prometheus scrape Kubernetes, Envoy và custom app targets         | targets/ServiceMonitor     | target screenshot/output  |
| OBS-002 | Required | Có RPS, p50/p95/p99, 2xx/4xx/429/5xx                              | PromQL/dashboard           | panels/query output       |
| OBS-003 | Required | Có Pod/node CPU, RAM và restart count                             | dashboard                  | panels                    |
| OBS-004 | Required | Có retrieval, generation và ingestion metrics                     | PromQL                     | query output              |
| OBS-005 | Required | FastAPI/ingestion gửi structured logs qua OTLP Collector tới Loki | query theo request ID      | log result                |
| OBS-006 | Required | Logs có service/event/request ID/trace ID/status/duration         | LogQL/sample               | sample redacted log       |
| OBS-007 | Required | Logs không chứa raw secret/prompt/document theo policy            | tests/sample review        | report                    |
| OBS-008 | Required | OTel traces đi qua Collector tới Tempo                            | trace query                | trace screenshot          |
| OBS-009 | Required | Trace có embed/search/build-prompt/generate spans                 | inspect trace              | span tree                 |
| OBS-010 | Required | Trace ID xuất hiện trong API response và logs                     | correlation test           | response/log/trace        |
| OBS-011 | Required | Pyroscope SDK gửi profile trực tiếp, không privileged/eBPF        | inspect Pod/profile        | flame graph/spec          |
| OBS-012 | Required | Grafana data sources/dashboard provision từ Git                   | redeploy Grafana           | provision files/dashboard |
| OBS-013 | Required | Không cài Alloy/agent trùng vai trò                               | package/resource inventory | inventory                 |
| OBS-014 | Required | Retention/storage/resource limits phù hợp ngân sách               | config + usage dashboard   | values/usage              |

## 10. Alerting

| ID      | Mức      | Tiêu chí                                                | Cách kiểm chứng         | Evidence tối thiểu     |
| ------- | -------- | ------------------------------------------------------- | ----------------------- | ---------------------- |
| ALT-001 | Required | Telegram contact point dùng Secret, không hardcode      | config/secret review    | redacted manifest      |
| ALT-002 | Required | Test notification tới Telegram thành công               | send test               | screenshot             |
| ALT-003 | Required | High latency/error alert được provision                 | inspect rule            | rule YAML              |
| ALT-004 | Required | High memory/restart alert được provision                | inspect rule            | rule YAML              |
| ALT-005 | Required | Ingestion failure alert được provision                  | inject flow failure     | Telegram + logs        |
| ALT-006 | Required | PostgreSQL unavailable/replication alert được provision | safe simulation/query   | rule/evidence          |
| ALT-007 | Required | Rate-limit spike alert được provision                   | k6 rate test            | dashboard + Telegram   |
| ALT-008 | Required | Ít nhất một alert có đủ Pending→Firing→Resolved         | synthetic/real workload | timestamps/screenshots |

## 11. Load và stress testing

| ID       | Mức      | Tiêu chí                                                | Cách kiểm chứng       | Evidence tối thiểu          |
| -------- | -------- | ------------------------------------------------------- | --------------------- | --------------------------- |
| PERF-001 | Required | `tests/k6/load.js` có ramp và thresholds                | review/run k6         | script + summary            |
| PERF-002 | Required | `tests/k6/rate-limit.js` chứng minh `429`               | run k6                | summary/status distribution |
| PERF-003 | Required | Cùng test window hiển thị RPS/latency/CPU/RAM/error     | timestamp correlation | dashboard screenshot        |
| PERF-004 | Required | p95/p99 và error rate được ghi vào report               | export summary        | report JSON/MD              |
| PERF-005 | Required | Test có stop condition, không làm hỏng data/cluster     | review/test           | post-test health            |
| PERF-006 | Required | Resource bottleneck/maximum safe demo load được ghi lại | analyze test          | conclusion/report           |

## 12. Source và software supply-chain security

| ID      | Mức      | Tiêu chí                                                    | Cách kiểm chứng                       | Evidence tối thiểu  |
| ------- | -------- | ----------------------------------------------------------- | ------------------------------------- | ------------------- |
| SEC-001 | Required | Custom image final dùng Chainguard base                     | inspect SBOM/image history/Dockerfile | report              |
| SEC-002 | Required | Semgrep pass theo config đã commit                          | CI/local scan                         | SARIF/log           |
| SEC-003 | Required | Trivy filesystem/config/secret pass                         | CI/local scan                         | report              |
| SEC-004 | Required | Trivy image pass policy HIGH/CRITICAL hoặc exception hợp lệ | image scan                            | report/exception    |
| SEC-005 | Required | Mỗi custom image có SBOM SPDX hoặc CycloneDX                | inspect artifact                      | SBOM files          |
| SEC-006 | Required | Cosign ký từng image theo immutable digest                  | `cosign verify`                       | verification output |
| SEC-007 | Required | Deployment dùng digest, không dùng `latest`                 | render manifests                      | rendered YAML       |
| SEC-008 | Required | CI permissions là least privilege và secret không in log    | workflow review                       | checklist           |
| SEC-009 | Required | Branch rules yêu cầu PR và required CI checks               | repository settings                   | screenshot/config   |
| SEC-010 | Optional | Admission policy từ chối image chưa ký                      | deploy signed/unsigned                | admission evidence  |

## 13. Documentation, operation và release

| ID      | Mức      | Tiêu chí                                                                     | Cách kiểm chứng        | Evidence tối thiểu |
| ------- | -------- | ---------------------------------------------------------------------------- | ---------------------- | ------------------ |
| DOC-001 | Required | README có prerequisites, install, configure, test, uninstall                 | reviewer walkthrough   | README review      |
| DOC-002 | Required | Architecture và data/telemetry flows khớp implementation                     | compare docs/manifests | review checklist   |
| DOC-003 | Required | Runbook có Pod crash, DB failover, ingestion failure, latency/disk/model OOM | tabletop test          | runbook            |
| DOC-004 | Required | Clean install từ environment sạch thành công                                 | follow docs/scripts    | install log        |
| DOC-005 | Required | Smoke test xác nhận service/data/observability sau install                   | run smoke suite        | report             |
| DOC-006 | Required | Demo script 12–15 phút có fallback fixture/evidence                          | rehearsal              | script/timing      |
| DOC-007 | Required | Required acceptance items đều Pass                                           | matrix review          | signed checklist   |
| DOC-008 | Required | Release dùng image digests, tag Git và release notes                         | inspect release        | tag/notes          |
| DOC-009 | Required | Limitations, trade-offs, cost và resource usage được công bố                 | review docs            | final report       |

## 14. Exit criteria

Release được phép tạo khi:

- Không có Required item ở trạng thái `Fail`, `Blocked` hoặc `Not started`.
- CI trên release commit pass.
- Trivy/Semgrep/Cosign verification pass theo policy.
- Clean install và smoke test pass.
- Demo rehearsal pass trong thời lượng mục tiêu.
- Secret scan và Git working tree sạch.
