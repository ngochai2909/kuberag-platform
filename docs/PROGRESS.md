# KubeRAG Progress

This file is the shared progress tracker for the two-person KubeRAG project. Update it after each approved phase, PR, or major verification run so both contributors can quickly see what is done, what is pending, and where to continue.

## Current Snapshot

- Current working branch: `feat/kuberag-rag-api-monorepo`
- Latest implementation commit: `dcbddbd feat: bootstrap KubeRAG RAG API monorepo`
- PR status: branch pushed; merge to `main` is still required through GitHub PR rules.
- Direct push to `main`: blocked by repository rules, as expected.
- Last full local verification: `make check` passed.
- Runtime cloud/Kubernetes environment: not created yet.

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

## In Progress / Local Changes

- `.github/dependabot.yml` has been deleted locally by the project owner to stop Dependabot update branches/PRs.
- This progress file is being added after phase 2 to support two-person coordination.

## Not Done Yet

The following required scopes are not implemented yet:

- Terraform GCP infrastructure.
- Ansible k3s setup.
- Kubernetes namespaces and Pod Security `restricted` validation.
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
- Runtime evidence under `docs/evidence/`.

## Recommended Next Phase

Next recommended work: **Infrastructure and k3s foundation**, not database yet.

Suggested scope:

- Add Terraform skeleton for GCP VPC, firewall, VM, disk, and outputs.
- Add Ansible skeleton for OS prerequisites and k3s server/worker join.
- Add Makefile targets for non-mutating infra checks.
- Add docs/runbook for infra setup and teardown.
- Add static tests/checks where possible.
- Do not run cloud `apply` unless explicitly approved.

Relevant acceptance groups:

- `INF-*` for infrastructure as code.
- `K8S-*` for cluster and Pod Security foundation.
- Later `NET-*` for Envoy Gateway.

## Coordination Notes

- Contributor A can continue backend/app work after infra foundation is clear.
- Contributor B can own Terraform/Ansible/Kubernetes foundation.
- Do not start PostgreSQL/pgvector until the cluster foundation plan is approved or a local-only DB schema phase is explicitly chosen.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
