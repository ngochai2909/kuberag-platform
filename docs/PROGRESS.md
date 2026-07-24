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

Status: In progress only for remaining Ansible install/idempotency evidence; Kubernetes and Envoy smoke routing are verified locally.

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

Pending in this foundation phase:

- Capture a clean Ansible install recap for `INF-003` and a second idempotent run for `INF-004`.

## In Progress / Local Changes

- Declarative Envoy Gateway manifests, repeatable smoke verification, updated runbook, and runtime evidence are ready for review.

## Not Done Yet

The following required scopes are not implemented yet:

- Terraform GCP infrastructure.
- Application routes from `/` to React and `/api/` to FastAPI.
- Envoy Gateway rate limiting and the `429` load test.
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
- Runtime evidence for the remaining platform phases.

## Recommended Next Phase

Close the remaining Ansible install/idempotency evidence, commit this foundation checkpoint, then begin the local PostgreSQL/pgvector foundation with one CloudNativePG instance.

Suggested scope:

- Capture `INF-003` and `INF-004` without reinstalling or destroying the healthy cluster.
- Install and verify the CloudNativePG operator using the approved Helm workflow.
- Add a single-instance PostgreSQL/pgvector cluster with persistent storage for local use.
- Add schema migration groundwork only after persistence and extension checks pass.
- Do not create GCP resources unless explicitly approved.

Relevant acceptance groups:

- Remaining `INF-*` evidence for installation and idempotency.
- `DB-001`, `DB-003`, `DB-004`, and `DB-010` for the local database foundation.

## Coordination Notes

- Contributor A can continue backend/app work against provider-independent interfaces.
- Contributor B can own Terraform/Ansible/Kubernetes and database platform work.
- Keep the local database scope single-instance; replication/failover remains deferred to the final 1-server + 2-worker topology.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
