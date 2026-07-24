# KubeRAG Progress

This file is the shared progress tracker for the two-person KubeRAG project. Update it after each approved phase, PR, or major verification run so both contributors can quickly see what is done, what is pending, and where to continue.

## Current Snapshot

- Current working branch: `docs/readme-single-node-target`.
- Branch baseline: `16495f1 docs: document temporary single-node target`.
- Remote status before this checkpoint: `origin/main` remains at `8064804`; this branch requires review/merge through repository rules.
- Last full application verification: `make check` passed in this checkpoint (`35 passed`, `98.41%` coverage).
- Runtime environment: local single-node k3s `v1.35.5+k3s1` is running on `hainguyenpc`; GCP resources have not been created.
- Local tooling: Helm `v4.2.2`; Envoy Gateway controller/chart `v1.8.3` in `gateway-system`.

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

Status: In progress on local single-node k3s.

Completed locally:

- Installed and verified local k3s `v1.35.5+k3s1` single-node cluster on `hainguyenpc`.
- Disabled Traefik and applied node labels `kuberag.io/topology=single-node` and `kuberag.io/role=all-in-one`.
- Applied the Kustomize local foundation overlay.
- Created namespaces: `rag`, `data`, `prefect`, `loadtest`, `observability`, and `gateway-system`.
- Enforced Pod Security Standards `restricted` on custom workload namespaces.
- Deployed restricted smoke workload `kuberag-pss-smoke` in `rag`.
- Verified an unsafe privileged/root Pod is rejected by admission.
- Installed Helm `v4.2.2` and Envoy Gateway controller/chart `v1.8.3` in `gateway-system`.
- Verified the Envoy Gateway controller deployment is `Available` with one `Running` Pod and zero restarts.

Verification/evidence:

- `docs/evidence/K8S-001/nodes-wide.txt`
- `docs/evidence/K8S-002/nodes-labels.txt`
- `docs/evidence/K8S-003/namespaces-pss-labels.txt`
- `docs/evidence/K8S-004/rag-smoke-pods-services.txt`
- `docs/evidence/K8S-004/rag-smoke-deployment-yaml.txt`
- `docs/evidence/K8S-005/unsafe-root-pod-rejected.txt`
- `docs/evidence/NET-001/envoy-controller-progress.txt` (partial; not acceptance pass)

Pending in this foundation phase:

- Capture a clean Ansible install recap for `INF-003` and a second idempotent run for `INF-004`.
- Add declarative `GatewayClass`, `Gateway`, and `HTTPRoute` manifests.
- Use local listener port `8080` because Apache owns host port `80` outside KubeRAG.
- Capture Accepted/resolved conditions and an HTTP smoke result before marking `NET-001` Pass.
- Prove Traefik does not serve any KubeRAG route.

## In Progress / Local Changes

- Local single-node foundation, pinned K3s automation, Envoy controller checkpoint, and evidence are being prepared for commit.

## Not Done Yet

The following required scopes are not implemented yet:

- Terraform GCP infrastructure.
- Envoy Gateway routing and gateway rate limiting.
- PostgreSQL/pgvector and CloudNativePG.
- Alembic migrations and database schema.
- Prefect ingestion flows for VnExpress RSS and NVD API.
- Embedding model integration.
- llama.cpp self-hosted generation client/deployment.
- React/Vite frontend.
- Full OpenTelemetry, Prometheus, Loki, Tempo, Pyroscope, Grafana dashboards, and alerts.
- k6 load and rate-limit tests.
- Chainguard image hardening for all custom images.
- Semgrep, Trivy, SBOM, Cosign signing/verification.
- Complete runtime evidence for gateway routing and all later platform phases.

## Recommended Next Phase

Next recommended work: **Envoy Gateway foundation on local single-node k3s**, not database yet.

Suggested scope:

- Add declarative Gateway API manifests for a minimal HTTP smoke route.
- Configure the local Envoy listener on port `8080`; keep Apache unchanged on port `80`.
- Verify `GatewayClass`, `Gateway`, and `HTTPRoute` conditions are Accepted/resolved.
- Prove Traefik is not serving KubeRAG routes.
- Capture `NET-001` route condition evidence and a basic HTTP smoke result.
- Do not create GCP resources unless explicitly approved.

Relevant acceptance groups:

- Remaining `INF-*`/`K8S-*` evidence for idempotency and runtime inspection.
- `NET-*` for Envoy Gateway, routing, and later rate limiting.

## Coordination Notes

- Contributor A can continue backend/app work after infra foundation is clear.
- Contributor B can own Terraform/Ansible/Kubernetes foundation.
- Do not start PostgreSQL/pgvector until the cluster foundation plan is approved or a local-only DB schema phase is explicitly chosen.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
