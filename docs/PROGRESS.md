# KubeRAG Progress

This file is the shared progress tracker for the two-person KubeRAG project. Update it after each approved phase, PR, or major verification run so both contributors can quickly see what is done, what is pending, and where to continue.

## Current Snapshot

- Current working branch: `feat/gcp-single-node-foundation`.
- Branch baseline: `1430b9a Merge pull request #12 from ngochai2909/docs/readme-single-node-target`.
- Remote baseline before this checkpoint: `origin/main` is `1430b9a`; this branch requires review/merge through repository rules.
- Last full application verification: `make check` passed in this checkpoint (`35 passed`, `98.41%` coverage).
- Runtime environment: single-node k3s `v1.35.5+k3s1` is running locally on `hainguyenpc` and on the temporary GCP VM `kuberag-server`; GCP administration and Kubernetes API access use IAP tunnels.
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

Status: Terraform, IAP, persistent storage, and the GCP single-node k3s foundation are applied and verified. Envoy deployment on GCP is pending.

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
  backend, GatewayClass, Gateway, and HTTPRoute. It listens on port `8080` to
  match the existing restricted GCP firewall rule; runtime deployment remains
  pending.

Pending:

- Deploy the Envoy smoke route through the GCP external address.

## In Progress / Local Changes

- GCP infrastructure and single-node k3s are applied with Terraform and
  Ansible idempotency verified. The next checkpoint is the Kubernetes
  foundation and Envoy smoke route on GCP.

## Not Done Yet

The following required scopes are not implemented yet:

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

Deploy and verify the existing restricted Kubernetes foundation and Envoy smoke
route on the GCP cluster before deploying data workloads.

Suggested scope:

- Apply the namespace and Pod Security Standards foundation to GCP.
- Install Envoy Gateway and apply the GCP Gateway API overlay.
- Verify the smoke route through the GCP external address on port `8080`.
- Keep PostgreSQL/pgvector pending until the GCP foundation and storage design pass.

Relevant acceptance groups:

- `INF-001` through `INF-006` for GCP infrastructure, idempotency, cost control, and secret hygiene.

## Coordination Notes

- Contributor A can continue backend/app work against provider-independent interfaces.
- Contributor B can own Terraform/Ansible/Kubernetes and database platform work.
- Keep the local database scope single-instance; replication/failover remains deferred to the final 1-server + 2-worker topology.
- Keep every phase small enough to review independently.
- Update this file whenever a phase changes status or important verification is run.
