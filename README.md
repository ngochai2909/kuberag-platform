# KubeRAG Platform

KubeRAG is a cloud-native RAG platform monorepo. The target platform uses FastAPI, PostgreSQL/pgvector, Prefect, React/Vite, Envoy Gateway, OpenTelemetry, Prometheus/Grafana, and a self-hosted llama.cpp model on Kubernetes.

The current infrastructure target is a **temporary single-node k3s environment** for local development and constrained demo work. The final target remains the original cluster shape: **1 k3s server/control-plane node and 2 k3s worker nodes** on GCP Compute Engine.

Current repository state: **phase 2 RAG API skeleton**. The FastAPI backend lives in `apps/rag-api`, exposes the KubeRAG query contract, and no longer depends on LangGraph, LangChain, OpenAI SDKs, or an external LLM API. PostgreSQL/pgvector retrieval and llama.cpp generation providers are intentionally not implemented yet.

## Requirements

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker, only if building or running the local backend container
- Linux host with sudo access for local k3s
- Terraform for infrastructure validation
- Ansible for local k3s host configuration
- kubectl after k3s install; Helm before installing platform charts

Validated local platform versions:

- k3s `v1.35.5+k3s1`
- Helm `v4.2.2`
- Envoy Gateway Helm chart `v1.8.3`

## Quick Start

```bash
cp .env.example .env
make setup
make run
```

Open `http://localhost:8000/docs` in development.

During phase 2, `/health/live` is healthy when the process is running. `/health/ready` returns `503` unless a `RagService` implementation is injected by tests or a future provider wiring phase. This is expected because real PostgreSQL/pgvector and llama.cpp providers are not part of this phase.

The public API contract is:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is KubeRAG?","top_k":5}'
```

Without a configured `RagService`, this endpoint returns a safe `503` response. Unit and integration tests inject a fake service to verify request/response behavior without network access.

## Commands

```bash
make setup         # install from the lockfile
make run           # run the FastAPI backend from apps/rag-api
make test          # run backend tests and coverage gate
make lint          # Ruff linting for backend source/tests
make format        # format backend source/tests
make format-check  # verify formatting without modifying files
make typecheck     # mypy for backend source/tests
make check         # lint, format-check, typecheck, and test
make lock          # intentionally refresh uv.lock
```

## Local k3s Foundation

The current infrastructure phase is local single-node k3s. It does not create GCP resources. Envoy Gateway is installed with Helm; project-owned Gateway API resources and the restricted smoke backend are managed with Kustomize.

```bash
make infra-check
make k3s-install
export KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml"

helm upgrade --install envoy-gateway \
  oci://docker.io/envoyproxy/gateway-helm \
  --version v1.8.3 \
  --namespace gateway-system \
  --create-namespace
kubectl wait --timeout=5m --namespace gateway-system \
  deployment/envoy-gateway --for=condition=Available

make k3s-foundation-apply
make k3s-foundation-status
make k3s-foundation-smoke
make k3s-unsafe-check
```

The local Gateway listens on `<node-ip>:8080` so Apache can continue using host port `80`. The local smoke route sends `/hostname` through Envoy to `kuberag-pss-smoke`; later application manifests replace it with `/` for React and `/api/` for FastAPI.

See `docs/runbooks/local-k3s-foundation.md` for evidence capture and rollback notes.

## GCP Single-Node Preflight

The next checkpoint moves the same single-node foundation to GCP Compute
Engine. Billing, the Compute Engine API, local Application Default Credentials,
the Singapore zone, the target E2 machine type, and a dedicated SSH key must be
verified before Terraform is allowed to create resources.

```bash
gcloud config get-value project
gcloud services list --enabled \
  --filter="config.name:compute.googleapis.com" \
  --format="value(config.name)"
gcloud auth application-default print-access-token >/dev/null \
  && echo "ADC: OK"
```

No VM is created during preflight. Review `terraform plan` before any
`terraform apply`. See `docs/runbooks/gcp-cost-control.md` for the budget and
manual stop/start/destroy procedure.

## Monorepo Layout

```text
apps/
  rag-api/          FastAPI RAG API skeleton
  ingestion/        Placeholder for Prefect ingestion flows
  frontend/         Placeholder for React/Vite UI
infra/
  terraform/        Placeholder for GCP infrastructure as code
  ansible/          Placeholder for k3s host configuration
deploy/
  helm/             Placeholder for project-owned Helm assets
  kustomize/        Placeholder for Kubernetes workload bases and overlays
observability/
  collector/        Placeholder for OpenTelemetry Collector config
  dashboards/       Placeholder for Grafana dashboards
  alerts/           Placeholder for alerting config
tests/
  k6/               Placeholder for load and rate-limit tests
docs/
  evidence/         Runtime evidence grouped by acceptance criterion
  runbooks/         Operational procedures
```

## Phase Boundaries

Phase 2 only replaces the legacy agent backend with typed RAG API interfaces and a deterministic skeleton. It does not implement PostgreSQL, pgvector, ingestion, llama.cpp HTTP calls, Envoy Gateway, frontend, observability, supply-chain scanning, or Kubernetes manifests.

The current implementation phase is the single-node foundation: local automation for one node, Ansible k3s setup, namespace and Pod Security `restricted` validation, and then a minimal Envoy Gateway route. PostgreSQL/pgvector and ingestion come after that foundation is verified.

The single-node target is temporary. The 3-node GCP topology and PostgreSQL primary/replica placement must be restored before final acceptance.

## Security Notes

- Do not commit real `.env` files, credentials, kubeconfig, Terraform state, tokens, or private keys.
- Rate limiting belongs at Envoy Gateway, not inside FastAPI.
- Future custom container images must use approved Chainguard bases and run as non-root.
- Unit tests must remain deterministic and must not call live external services.
- RAG prompts treat retrieved documents as untrusted data, not instructions.
