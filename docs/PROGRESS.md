# KubeRAG Progress

This file is the shared progress tracker for the two-person KubeRAG project. Update it after each approved phase, PR, or major verification run so both contributors can quickly see what is done, what is pending, and where to continue.

## Current Snapshot

- Current working branch: `docs/readme-single-node-target`.
- Branch baseline: `16495f1 docs: document temporary single-node target`.
- Remote status before this checkpoint: `origin/main` remains at `8064804`; this branch requires review/merge through repository rules.
- Last full application verification: `make check` passed in this checkpoint (`35 passed`, `98.41%` coverage).
- Runtime environment: local single-node k3s `v1.35.5+k3s1` is running on `hainguyenpc`; GCP preflight is complete and no GCP resources have been created.
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

### Phase 4 - GCP Single-Node Foundation

Status: Preflight complete; Terraform implementation and plan are pending.

Completed:

- Selected project `kube-rag-platform` with billing enabled.
- Enabled the Compute Engine API and verified local Application Default Credentials.
- Verified `asia-southeast1-b` is available and `e2-standard-2` provides 2 vCPU and 8 GiB RAM.
- Created a dedicated local Ed25519 SSH key for the GCP VM; private key material remains outside Git.
- Created a VND 3,000,000 monthly billing-account budget alert and documented cost-control operations.
- Captured `docs/evidence/INF-005/budget-alert.png` and `budget-alert.md`.

Pending:

- Implement Terraform for the custom VPC, subnet, least-privilege firewall, static address, and one VM.
- Run `terraform init`, format, validate, and review `terraform plan` before apply.
- Apply only after explicit approval, then capture the clean Ansible install and idempotent second run.
- Deploy the Envoy smoke route through the GCP external address.

## In Progress / Local Changes

- GCP single-node Terraform design is the next implementation checkpoint; cloud resources have not been created.

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

Implement and review the GCP single-node Terraform plan. Use the new VM as the clean environment for `INF-003` and the second Ansible run for `INF-004` before deploying data workloads.

Suggested scope:

- Add Terraform configuration for one GCP server while keeping a path to two workers.
- Restrict SSH and Kubernetes API access to the administrator CIDR.
- Review the exact resource plan and expected cost before apply.
- Capture clean-install and idempotency evidence on the new VM.
- Keep PostgreSQL/pgvector pending until the GCP foundation and storage design pass.

Relevant acceptance groups:

- `INF-001` through `INF-006` for GCP infrastructure, idempotency, cost control, and secret hygiene.

## Coordination Notes

- Contributor A can continue backend/app work against provider-independent interfaces.
- Contributor B can own Terraform/Ansible/Kubernetes and database platform work.
- Keep the local database scope single-instance; replication/failover remains deferred to the final 1-server + 2-worker topology.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
