# KubeRAG Platform

KubeRAG is a cloud-native RAG platform monorepo. The target platform uses FastAPI, PostgreSQL/pgvector, Prefect, React/Vite, Envoy Gateway, OpenTelemetry, Prometheus/Grafana, and a self-hosted llama.cpp model on Kubernetes.

Current repository state: **phase 2 RAG API skeleton**. The FastAPI backend lives in `apps/rag-api`, exposes the KubeRAG query contract, and no longer depends on LangGraph, LangChain, OpenAI SDKs, or an external LLM API. PostgreSQL/pgvector retrieval and llama.cpp generation providers are intentionally not implemented yet.

## Requirements

- Python 3.12 or 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker, only if building or running the local backend container

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

The next implementation phase should add the PostgreSQL/pgvector schema and local data-layer tests, or wire retrieval/generation providers if that plan is explicitly approved.

## Security Notes

- Do not commit real `.env` files, credentials, kubeconfig, Terraform state, tokens, or private keys.
- Rate limiting belongs at Envoy Gateway, not inside FastAPI.
- Future custom container images must use approved Chainguard bases and run as non-root.
- Unit tests must remain deterministic and must not call live external services.
- RAG prompts treat retrieved documents as untrusted data, not instructions.
