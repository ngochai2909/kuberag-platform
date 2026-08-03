# KubeRAG Progress

This file is the detailed shared progress tracker for the two-person KubeRAG
project. For a shorter deployed-versus-prepared overview, read
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) first. Update both files after each
approved phase, PR, or major verification run.

## Current Snapshot

- Last updated: 2026-08-03.
- Current tracked release branch: `main`.
- Latest immutable release-manifest merge: `43871eb` (PR #26).
- Last full application verification: `make check` passed (`100 passed`, `2 skipped`,
  `85.91%` coverage). The skipped tests require an explicit `DATABASE_URL` and
  are run against the GCP database through the controlled tunnel command.
- Runtime environment: one `v1.35.5+k3s1` node runs locally on `hainguyenpc` and one runs on the temporary GCP VM `kuberag-server`. They are separate clusters, not two nodes in one cluster.
- GCP access: SSH and local `kubectl` use IAP tunnels. Envoy Gateway `v1.8.3` and the smoke route are verified on GCP through public port `8080`.
- Tooling: Helm `v4.2.2`; Envoy Gateway chart `v1.8.3` verified on local and GCP clusters.
- GCP user-facing demo: `kuberag-web`, `kuberag-rag-api`, and `kuberag-llm` are
  Ready in namespace `rag`. Envoy serves the React SPA at `/` and FastAPI at
  `/api/`; `/hostname` remains the separate smoke route.
- Immutable GCP release: API, frontend, Prefect server and Prefect worker were
  rolled out from CI-produced Artifact Registry digests after image scan, SBOM
  generation and Cosign verification. Runtime digest evidence is
  `docs/evidence/SEC-007/`.
- GCP observability: Prometheus, Grafana, Loki, Tempo, Pyroscope, and
  `kuberag-otel-collector` are Running as private `ClusterIP` workloads in
  `observability`. FastAPI four-signal evidence and Prefect ingestion
  telemetry evidence are captured under `docs/evidence/OBS-*`
  (2026-07-31). Envoy is a Prometheus scrape target; the post-release API and
  Envoy targets were both `up=1`.

## Completed Work

### Phase 1 - Monorepo Bootstrap

Status: Done on branch `feat/kuberag-rag-api-monorepo`.

Completed:

- Moved the existing FastAPI backend into `apps/rag-api`.
- Kept the Python package name `app` to avoid unnecessary import churn.
- Added skeleton directories for `apps/ingestion`, `apps/frontend`, `infra`, `deploy`, `observability`, `tests/k6`, `docs/runbooks`, and `docs/evidence`.
- Updated root tooling paths in `Makefile`, `pyproject.toml`, CI, Docker Compose, and backend Dockerfile path.
- Added a layout regression test for the monorepo skeleton.
- Added/kept project docs under `docs/` as the architecture source of truth.

Verification:

- `make check` passed after phase 1.

### Phase 2 - RAG API Skeleton

Status: Done on branch `feat/kuberag-rag-api-monorepo`.

Completed:

- Removed the legacy LangGraph/OpenAI agent main path.
- Removed `langchain`, `langgraph`, `langchain-openai`, `openai`, and `langsmith` dependencies from `pyproject.toml` and `uv.lock`.
- Replaced legacy `/api/v1/chat` with `POST /api/v1/query`.
- Added typed RAG interfaces: `Retriever`, `Generator`, `RagService`, and `RagPipelineService`.
- Added bounded RAG prompt builder that treats retrieved documents as untrusted data.
- Added response contract with `answer`, `sources`, `request_id`, `trace_id`, `retrieval_ms`, `generation_ms`, and `total_ms`.
- Added request ID and trace ID propagation skeleton.
- Added `/health/live`, `/health/ready`, `/api/v1/status`, and a minimal `/metrics` endpoint.
- Updated tests to use a fake `RagService`; no unit/integration test calls external services.
- Updated `README.md`, `AGENTS.md`, `.env.example`, and `evals/` for RAG skeleton state.

Verification:

- `uv lock` passed.
- `uv sync --frozen --group dev` passed and pruned legacy packages.
- `make check` passed.
- Final phase 2 test result: `35 passed`, coverage `98.41%`.

### Phase 3 - Local k3s Foundation

Status: Done for the temporary local single-node foundation; Kubernetes and Envoy smoke routing are verified locally.

Completed locally:

- Installed and verified local k3s `v1.35.5+k3s1` single-node cluster on `hainguyenpc`.
- Disabled Traefik and applied node labels `kuberag.io/topology=single-node` and `kuberag.io/role=all-in-one`.
- Created namespaces: `rag`, `data`, `prefect`, `loadtest`, `observability`, and `gateway-system`.
- Enforced Pod Security Standards `restricted` on custom workload namespaces.
- Deployed restricted smoke workload `kuberag-pss-smoke` in `rag`.
- Verified an unsafe privileged/root Pod is rejected by admission.
- Installed Helm `v4.2.2` and Envoy Gateway controller/chart `v1.8.3` in `gateway-system`.
- Added declarative `GatewayClass`, `Gateway`, and local smoke `HTTPRoute` manifests to Kustomize.
- Patched the local listener to port `8080` while keeping base port `80` for the later cloud overlay.
- Verified GatewayClass `Accepted=True`, Gateway `Programmed=True`, HTTPRoute `Accepted=True`/`ResolvedRefs=True`, and an HTTP request through Envoy to the smoke Pod.
- Verified Traefik is absent and does not serve a KubeRAG route.

Verification/evidence:

- `docs/evidence/K8S-001/nodes-wide.txt`
- `docs/evidence/K8S-002/nodes-labels.txt`
- `docs/evidence/K8S-003/namespaces-pss-labels.txt`
- `docs/evidence/K8S-004/rag-smoke-pods-services.txt`
- `docs/evidence/K8S-004/rag-smoke-deployment-yaml.txt`
- `docs/evidence/K8S-005/unsafe-root-pod-rejected.txt`
- `docs/evidence/NET-001/gateway-api-smoke.txt`
- `docs/evidence/NET-004/kube-system-no-traefik.txt`

### Phase 4 - GCP Single-Node Foundation

Status: Done for the temporary GCP single-node foundation, including Envoy Gateway smoke routing and PSS checks.

Completed:

- Selected project `kube-rag-platform` with billing enabled.
- Enabled the Compute Engine API and verified local Application Default Credentials.
- Verified `asia-southeast1-b` is available and `e2-standard-2` provides 2 vCPU and 8 GiB RAM.
- Created a dedicated local Ed25519 SSH key for the GCP VM; private key material remains outside Git.
- Created a VND 3,000,000 monthly billing-account budget alert and documented cost-control operations.
- Captured `docs/evidence/INF-005/budget-alert.png` and `budget-alert.md`.
- Added the Terraform root module for the custom VPC, subnet, restricted
  firewall rules, static external IP, one 8 vCPU/16 GiB VM, and separate boot
  and data disks.
- Initialized the local backend and locked `hashicorp/google v7.41.0`.
- Passed `terraform fmt -check` and `terraform validate` on 2026-07-27.
- Created ignored local inputs and reviewed the saved Terraform plan on
  2026-07-27: `8 to add, 0 to change, 0 to destroy`.
- Increased the separate data disk from 100 GiB to 150 GiB before apply to
  leave headroom for k3s data, PostgreSQL/pgvector, the pinned GGUF model, and
  short-retention observability data. The reviewed plan still has eight creates
  and no update or destroy action.
- Captured the redacted plan summary in
  `docs/evidence/INF-001/terraform-plan-summary.md`; the infrastructure apply
  is complete and the Kubernetes node inventory remains pending.
- Applied the initial foundation with `8 added, 0 changed, 0 destroyed`.
- Enabled IAP and added the restricted IAP SSH firewall with `2 added, 1 changed
  in-place, 0 destroyed`; no VM, disk, IP, or network was replaced.
- Verified `ssh kuberag-gcp` reaches `kuberag@kuberag-server` through IAP.
- Verified the VM is `RUNNING`, has 8 vCPU/16 GiB RAM, a 30 GiB boot disk, and
  an unformatted 150 GiB data disk.
- Ran the post-apply Terraform idempotency check: `No changes`, exit code `0`.
- Added a remote GCP Ansible inventory and syntax-checked playbook for guarded
  ext4 formatting/mounting and k3s installation on the persistent disk.
- Assigned non-overlapping k3s Pod/Service CIDRs `10.52.0.0/16` and
  `10.53.0.0/16` because the VPC subnet uses `10.42.0.0/24`.
- Verified Ansible reaches the VM through IAP and returns `ping: pong`.
- Formatted the previously empty 150 GiB data disk as ext4 and mounted it at
  `/var/lib/kuberag` using its stable GCE disk alias.
- Installed pinned k3s `v1.35.5+k3s1` with Traefik disabled and persistent data
  under `/var/lib/kuberag/k3s`.
- Verified the GCP control-plane node is `Ready` and the CoreDNS,
  local-path-provisioner, and metrics-server Pods are `Running`.
- Verified local `kubectl` access through the IAP tunnel on port `16443`.
- Re-ran the GCP Ansible playbook with `changed=0`, `unreachable=0`, and
  `failed=0`.
- Added and rendered the GCP Kustomize overlay for the restricted smoke
  backend, GatewayClass, Gateway, and HTTPRoute on port `8080`.
- Installed Envoy Gateway chart `v1.8.3` on GCP and applied the foundation
  overlay.
- Verified Gateway `Programmed=True`, HTTPRoute `Accepted`/`ResolvedRefs`,
  smoke Pod `Running`, and `curl http://<external-ip>:8080/hostname`.
- Verified an unsafe privileged/root Pod is rejected by PSS on GCP.
- Updated operator egress CIDRs in the ignored local `terraform.tfvars` after
  a company-network public IP change, then re-verified the smoke route.
- Captured GCP runtime evidence under `docs/evidence/K8S-*`, `NET-001`,
  `NET-004`, and `INF-002`.

### Phase 5 - PostgreSQL/pgvector Data Foundation

Status: CloudNativePG, PostgreSQL, pgvector, and the initial Alembic schema are
verified on the temporary GCP single-node cluster. Persistence restart testing
remains pending.

Completed:

- Installed CloudNativePG chart `0.29.0` / operator `1.30.0` in namespace
  `data` with single-namespace RBAC and PSS-restricted security contexts.
- Created `Cluster/kuberag-pg` with one PostgreSQL `18.4` instance and a 20 GiB
  `local-path` PVC on the dedicated GCP data disk.
- Created `Database/kuberag`; CNPG generated the application Secret and
  reconciled pgvector `0.8.5`.
- Added Alembic `20260728_0001` for `documents`, `chunks`, and
  `ingestion_runs`, including identity/chunk constraints and unbounded
  `vector` storage without a premature ANN index.
- Ran `alembic upgrade head` from the empty application database and reran it
  successfully as a no-op.
- Passed the synthetic vector insert/cosine-query integration test; the test
  transaction was rolled back.
- Captured evidence for `DB-001`, `DB-003` through `DB-007`.
- Passed `DB-010`: inserted synthetic marker
  `db-010-20260728T090636Z`, deleted only Pod `kuberag-pg-1`, waited for CNPG
  recreate, and verified the same checksum/count plus Bound PVC
  (`docs/evidence/DB-010/`).
- Added the `ingestion` package with shared `SourceDocument`, injectable
  `RetryingHttpClient`, and offline VnExpress adapter plus fixtures.
- Captured offline evidence for `ING-001`, `ING-003`, and `ING-004`
  (`ING-002` removed after NVD was deleted from the repository).
- Added sentence-aware chunking (`sentence-overlap-v1`) with configurable
  `max_chars`/`overlap_chars`, title prefixing, and boundary unit tests
  (`ING-009`).
- Added checksum-based document/chunk upsert, in-memory + Postgres stores, and
  `ingestion_runs` session counters (`ING-007`, `ING-008` offline).
- Added `EmbeddingProvider` + `FakeEmbeddingProvider` (384-dim) and wired
  batched embed into upsert (`ING-010` offline; real e5 deferred to cluster).
- Added Prefect 3 dependency and `daily_ingest_flow` skeleton with daily cron
  declaration plus offline end-to-end tests (`ING-005` config / `ING-006`
  offline).
- Added `apps/ingestion/Dockerfile` on Chainguard bases. Free `:latest` is
  CPython 3.14, so the builder installs managed 3.13 under `/python` and the
  runtime copies it with the venv. `make docker-ingestion-smoke` prints
  `kuberag-daily-ingest` and cron `0 2 * * *` UTC. Live crawl JSON in
  `tmp/vnexpress-smoke.json` is local reference only (no GCP upsert).
- Deployed Prefect server/worker to GCP namespace `prefect` using
  `kuberag-ingestion:local` (imported into k3s containerd). Added `tzdata` for
  Prefect/ZoneInfo. Bootstrap Job registered work pool `kuberag-ingestion` and
  deployment `kuberag-daily-ingest/daily` with cron `0 2 * * *` UTC
  (`docs/evidence/ING-005/gcp-prefect-schedule.txt`).
- Updated the registered Prefect deployment schedule to `0 3 * * *` UTC
  (10:00 Vietnam) by rebuilding/importing the ingestion image and rerunning
  the Bootstrap Job. The Job completed without executing ingestion
  (`docs/evidence/ING-005/gcp-prefect-schedule-1000-vietnam.txt`).
- Added optional extra `embedding` (sentence-transformers + torch CPU),
  `E5EmbeddingProvider`, PVC `kuberag-embedding-models`, download/smoke Jobs,
  and switched the GCP Prefect worker to `KUBERAG_EMBEDDING_MODE=e5`
  (`docs/evidence/ING-010/gcp-e5-smoke.txt`).
- Added a restricted `kuberag-ingest-run` trigger Job and `make gcp-ingest-run`.
  The first live attempt exposed missing PostgreSQL transaction commits; fixed
  the cluster runtime to use autocommit reads plus explicit store transactions.
- Completed the live VnExpress flow through real e5 into CloudNativePG.
  An early dual-source experiment briefly included NVD; NVD was later
  removed from scope, code, fixtures, and the live corpus. Stable
  VnExpress reruns skip unchanged records with zero SQL duplicates
  (`ING-006`–`ING-008` GCP evidence).
- Compressed the large Torch CPU image stream during k3s import and added a
  persistent uv build cache/longer HTTP timeout after transient network resets.
- Replaced Prefect Server's SQLite metadata PVC with a separate CNPG-managed
  PostgreSQL database/role `prefect`. The legacy SQLite PVC remains on the GCP
  cluster only for rollback and is no longer part of a clean install. A new
  Prefect bootstrap, worker restart, and manual flow run completed successfully
  without a `database is locked` log match
  (`docs/evidence/ING-005/prefect-postgresql-metadata.txt`).

## In Progress / Local Changes

### Phase 8 - Full-stack Observability

Status: Single-node observability is deployed with GCP runtime evidence for
`OBS-001`–`OBS-014`. Envoy Gateway data-plane metrics are scraped. Alertmanager
Slack lifecycle and bounded k6 runtime evidence are complete; UI screenshots
remain optional evidence.

Completed:

- Added Prometheus application metrics for HTTP request count/duration and RAG
  pipeline stages; `/metrics` is scraped through a project `ServiceMonitor`.
- Added OpenTelemetry SDK instrumentation for FastAPI and Prefect. FastAPI
  creates the request span plus `rag.embed_query`, `rag.pgvector_search`,
  `rag.build_prompt`, and `rag.llm_generate`; it returns the same trace ID in
  the response header/body and structured log.
- Installed the restricted single-node stack: kube-prometheus-stack (without
  privileged node exporter), Loki, Tempo, Pyroscope, and OTel Collector.
  Each has explicit resource limits, short retention, and persistent PVCs.
- Kept all observability Services private. Grafana access is IAP tunnel plus
  local `kubectl port-forward`; no new firewall rule or Envoy route was added.
- Provisioned Prometheus, Loki, Tempo, and Pyroscope Grafana data sources and
  a Git-managed `KubeRAG Overview` dashboard; verified via in-Pod Grafana API
  (`docs/evidence/OBS-012/`).
- Captured FastAPI four-signal evidence on 2026-07-31:
  `docs/evidence/OBS-001`–`OBS-014/` (PromQL, Loki structured metadata,
  Tempo span tree, Pyroscope render, correlation, no-Alloy, retention/PVC).
- Fixed short-lived Prefect OTLP drop by force-flushing exporters in
  `shutdown_ingestion_telemetry()`; rebuilt/imported `kuberag-ingestion:local`
  and restarted `prefect-worker`.
- Verified Prefect flow `0161776d-6e44-41c5-a9ac-64088949778c` Completed with
  Loki `service_name=kuberag-ingestion`, Tempo spans `ingestion.fetch` /
  `ingestion.upsert`, and Prometheus `kuberag_ingestion_*`
  (`docs/evidence/OBS-004/gcp-ingestion-metrics.txt`,
  `OBS-005/gcp-loki-ingestion-log.txt`,
  `OBS-008/gcp-tempo-ingestion-spans.txt`).

Alertmanager/Slack lifecycle is verified; keep the test-only rule deleted and
retain its redacted `ALT-008` evidence. The verified k6 bound is 3 VUs; the
rate-limit scenario closed `NET-006` and generated the expected `429` alert.

- Week 2 data/ingestion quality gate is complete on the temporary GCP
  single-node path.
- Added `PostgresRetriever`, which combines an `EmbeddingProvider` with a
  typed `VectorSearchStore`. `PostgresVectorStore` joins `chunks` to
  `documents`, orders by pgvector cosine distance, and preserves the VnExpress
  title/URL/source needed by the later API and frontend. Unit tests use fakes;
  a separately-invoked GCP database integration test inserts and removes only
  synthetic fixture data. Local unit/type/lint verification and the GCP
  pgvector integration test passed (`docs/evidence/RAG-002/`). The adapter is
  not deployed or wired to a generator yet.
- Deployed and verified llama.cpp with the pinned Qwen2.5-1.5B-Instruct GGUF
  `Q4_K_M` model in the `rag` namespace. The internal `ClusterIP` service
  passed `/health`, `/v1/models`, and an OpenAI-compatible chat completion via
  a temporary local tunnel (`docs/evidence/RAG-004/`).
- Added the real FastAPI composition root, a Chainguard-based API image, and
  restricted GCP Kustomize resources with a separate 2 GiB E5 cache PVC. The
  1.6 GiB image was imported through IAP and the Deployment is `1/1 Running`.
  An authenticated real query returned a generated answer, source URLs,
  request/trace IDs, and timing fields (`docs/evidence/RAG-006/`). The first
  cold request took 22.9s while the warm path took 8.07s; generation on the
  CPU-only Qwen Pod is the dominant latency.
- Added a React/Vite source-card UI with loading, error, shared-rate-limit,
  request/trace ID, timing, dark-mode, and optional VnExpress RSS thumbnail
  states. The API now exposes the document metadata image URL as
  `sources[].thumbnail_url`; neither the image binary nor its URL is sent to
  the generation prompt.
- Built the frontend as a non-root Nginx image, imported it into the GCP k3s
  container runtime, and deployed `kuberag-web` with restricted Pod Security
  settings. Envoy now routes `/` to the frontend and `/api/` to FastAPI; the
  smoke route moved to `/hostname` to prevent it from taking precedence over
  the UI.
- Changed only the GCP API overlay to explicit `PUBLIC_DEMO_MODE=true` with
  browser bearer authentication disabled. Envoy still owns the shared 10
  requests/minute limit. This is a constrained demo configuration, not the
  production authentication design.
- Increased the Envoy API route request timeout to 60 seconds (backend 55
  seconds), while FastAPI retains its 45-second bound. A real request through
  the Envoy data plane returned an answer and three source records with
  thumbnail URLs.

## Not Done Yet

The following required scopes are not implemented yet:

- Optional Grafana and Slack UI screenshots for the k6 rate-limit window. The
  runtime rate-limit Firing state, JSON summaries, resource snapshot, and
  Alertmanager delivery metrics are stored under `docs/evidence/PERF-*` and
  `docs/evidence/ALT-007/`.
- Repository-administration evidence for `SEC-009` branch protection.
- Full clean-install evidence in a genuinely isolated environment and final
  demo rehearsal. The app-only recovery run is recorded under
  `docs/evidence/DOC-004/` and must not be mislabeled as a clean install.

## Recommended Next Phase

The user-facing demo path and Week 4 observability evidence path are deployed.
Continue with Week 5 operational controls:

- Keep the verified 3-VU single-node bound for demos. Capture optional Grafana
  and Slack UI screenshots for the completed k6 rate-limit scenario; do not
  publicize the internal Alertmanager link.
- Replace temporary public-demo API access with a reviewed user/gateway
  authentication design before any broader deployment.

Relevant acceptance groups:

- `ING-001`–`ING-010` are Pass for the current offline/GCP evidence split.
- Next focus: runtime evidence for `RAG-005`–`RAG-009`, then frontend/routes.

## Coordination Notes

- Contributor A can continue backend/app work against provider-independent interfaces.
- Contributor B can own Terraform/Ansible/Kubernetes and database platform work.
- Keep the local database scope single-instance; replication/failover remains deferred to the final 1-server + 2-worker topology.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
